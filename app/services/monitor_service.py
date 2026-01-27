import asyncio
import httpx
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

# ... imports ...

async def check_single_monitor(monitor: Monitor, session):
    """
    Checks a single monitor and updates its status and logs the check.
    """
    url = monitor.url
    start_time = datetime.now(timezone.utc)
    status_code = None

    error_message = None
    is_up = False
    response_time = 0

    try:
        async with httpx.AsyncClient(timeout=monitor.timeout_seconds) as client:
            response = await client.get(url)
            status_code = response.status_code
            response_time = (datetime.now() - start_time).total_seconds()
            
            if monitor.expected_status:
                is_up = (status_code == monitor.expected_status)
            else:
                is_up = (200 <= status_code < 300)

    except httpx.RequestError as exc:
        error_message = f"Request error: {exc}"
        is_up = False
    except Exception as exc:
        error_message = f"Unexpected error: {exc}"
        is_up = False
    
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
        error_message=error_message,
        checked_at=datetime.now(timezone.utc) # explicit set
    )
    session.add(check_log)

    # Detect status change
    if previous_status is not None and previous_status != is_up:
        logger.info(f"Monitor {monitor.id} status changed: {previous_status} -> {is_up}")
        # TODO: Trigger notification
        from app.services.notification_service import send_notification
        await send_notification(monitor, previous_status, is_up)
    
    return is_up

async def check_all_monitors():
    """
    Retrieves all active monitors and checks them.
    This function handles its own database session.
    """
    async with async_session() as session:
        try:
            # Fetch active monitors, eagerly loading owner for notifications
            result = await session.execute(select(Monitor).where(Monitor.is_active == True).options(selectinload(Monitor.owner)))
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
