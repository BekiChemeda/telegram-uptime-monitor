import asyncio
import httpx
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
from app.database.connection import async_session
from app.models import Monitor, CheckLog
import logging
import socket
import ssl
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_ssl_expiry_days(url: str):
    """
    Checks the SSL certificate expiry for the given URL.
    Returns the number of days until expiry, or None if error/check inapplicable.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme != 'https':
            return None
            
        hostname = parsed.hostname
        port = parsed.port or 443
        
        def _get_cert():
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return ssock.getpeercert()

        # Run blocking socket op in thread pool
        cert = await asyncio.to_thread(_get_cert)
        
        not_after_str = cert['notAfter']
        # Format: 'May 26 23:59:59 2025 GMT'
        expiry_date = datetime.strptime(not_after_str, '%b %d %H:%M:%S %Y %Z')
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        delta = expiry_date - now
        return delta.days
    except Exception as e:
        logger.warning(f"SSL Check failed for {url}: {e}")
        return None

def is_in_maintenance(monitor: Monitor) -> bool:
    """Checks if the monitor is currently in a maintenance window."""
    now = datetime.now(timezone.utc)
    # We rely on eager loading or relationship access. 
    # Note: monitor.maintenance_windows might need to be eager loaded in check_all_monitors
    if not monitor.maintenance_windows:
        return False
        
    for window in monitor.maintenance_windows:
        if window.start_time <= now <= window.end_time:
            return True
    return False

async def perform_pro_check(monitor: Monitor):
    """
    Performs the check logic including retries, keywords, etc.
    Returns (status_code, response_time, is_up, error_message, extra_alerts)
    """
    retries = monitor.consecutive_checks if monitor.consecutive_checks > 0 else 1
    
    final_status_code = None
    final_response_time = 0
    final_is_up = False
    final_error = None
    extra_alerts = [] # List of strings like "High Latency", "SSL Expiring"

    for attempt in range(retries):
        try:
            start_time = datetime.now(timezone.utc)
            
            async with httpx.AsyncClient(timeout=monitor.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(monitor.url)
                
                # Basic metrics
                final_status_code = response.status_code
                final_response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                # 1. Status Check
                if monitor.expected_status:
                    check_ok = (final_status_code == monitor.expected_status)
                else:
                    check_ok = (200 <= final_status_code < 300)
                
                if not check_ok:
                    final_error = f"Unexpected Status: {final_status_code}"
                    final_is_up = False
                else:
                    # 2. Keyword Check (Only if status is OK)
                    text_body = response.text
                    
                    if monitor.keyword_include and monitor.keyword_include not in text_body:
                        final_error = f"Missing Keyword: '{monitor.keyword_include}'"
                        final_is_up = False
                        check_ok = False # Fail this attempt
                    
                    elif monitor.keyword_exclude and monitor.keyword_exclude in text_body:
                        final_error = f"Forbidden Keyword Found: '{monitor.keyword_exclude}'"
                        final_is_up = False
                        check_ok = False
                    else:
                        final_is_up = True
                        final_error = None

                # 3. Latency Check (Warning only, does not mark as DOWN unless it timed out which is caught elsewhere)
                if final_is_up and monitor.max_response_time and final_response_time > monitor.max_response_time:
                    extra_alerts.append(f"High Latency: {final_response_time:.2f}s > {monitor.max_response_time}s")

            # If UP, break retry loop immediately
            if final_is_up:
                break
            
            # If failed, and we have retries left, wait a bit
            if attempt < retries - 1:
                await asyncio.sleep(2) # Wait 2 seconds before retry
                
        except httpx.RequestError as exc:
            final_error = f"Request error: {exc}"
            final_is_up = False
            # continue retry
            if attempt < retries - 1:
                await asyncio.sleep(2)
        except Exception as exc:
            final_error = f"Unexpected error: {exc}"
            final_is_up = False
            break # Don't retry unexpected python errors usually

    # 4. SSL Check (Once, if UP or even if DOWN usually good to check if requested)
    # Perform outside retry loop to save time, or only if needed.
    if monitor.check_ssl:
        days_left = await get_ssl_expiry_days(monitor.url)
        if days_left is not None and days_left < monitor.ssl_expiry_days_threshold:
             extra_alerts.append(f"SSL Expiring in {days_left} days")

    return final_status_code, final_response_time, final_is_up, final_error, extra_alerts


async def check_single_monitor(monitor: Monitor, session):
    """
    Checks a single monitor and updates its status and logs the check.
    """
    # 0. Maintenance Check
    if is_in_maintenance(monitor):
        # logger.info(f"Monitor {monitor.id} is in maintenance window. Skipping.")
        return False # Or True? Skipping status update essentially.

    url = monitor.url
    
    # Perform Checks
    status_code, response_time, is_up, error_message, extra_alerts = await perform_pro_check(monitor)
    
    # Update monitor status
    previous_status = monitor.last_status # This might be None initially
    monitor.last_checked = datetime.now(timezone.utc)
    monitor.last_status = is_up
    
    # Log the check
    check_log = CheckLog(
        monitor_id=monitor.id,
        status_code=status_code,
        response_time=response_time,
        is_up=is_up,
        error_message=f"{error_message} | {', '.join(extra_alerts)}" if extra_alerts and error_message else (error_message or ', '.join(extra_alerts)),
        checked_at=datetime.now(timezone.utc) # explicit set
    )
    session.add(check_log)

    # Detect status change
    if previous_status is not None and previous_status != is_up:
        logger.info(f"Monitor {monitor.id} status changed: {previous_status} -> {is_up}")
        from app.services.notification_service import send_notification
        await send_notification(monitor, previous_status, is_up, error_message)
    
    # Send extra alerts (Stateless? Or only once? For now, let's send if they happen)
    # To avoid spamming latency alerts every minute, we ideally need state.
    # For now, we will piggyback on status change or send if meaningful.
    # Simplification: Only send extra alerts if status is UP (because if DOWN, that creates enough noise)
    if is_up and extra_alerts:
         # Check if we should throttle this? For now, just send distinct warning.
         pass 

    return is_up

async def check_all_monitors():
    """
    Retrieves all active monitors and checks them.
    This function handles its own database session.
    """
    async with async_session() as session:
        try:
            # Fetch active monitors, eagerly loading owner and maintenance windows
            stmt = select(Monitor).where(Monitor.is_active == True).options(
                selectinload(Monitor.owner),
                selectinload(Monitor.maintenance_windows)
            )
            result = await session.execute(stmt)
            monitors = result.scalars().all()
            
            if not monitors:
                # logger.debug("No active monitors found.")
                return

            tasks = []
            for monitor in monitors:
                # Basic interval check logic
                should_check = True
                if monitor.last_checked:
                    # ensure both are aware or both naive
                    last_checked = monitor.last_checked
                    if last_checked.tzinfo is None:
                         last_checked = last_checked.replace(tzinfo=timezone.utc)
                    
                    now = datetime.now(timezone.utc)
                    delta = (now - last_checked).total_seconds()
                    
                    if delta < monitor.interval_seconds:
                        should_check = False
                
                if should_check:
                    tasks.append(check_single_monitor(monitor, session))
            
            if tasks:
                await asyncio.gather(*tasks)
                await session.commit()
                logger.info(f"Checked {len(tasks)} monitors.")
            else:
                logger.debug("No monitors due for checking.")

        except Exception as e:
            logger.error(f"Error during monitoring cycle: {e}")
            await session.rollback()
