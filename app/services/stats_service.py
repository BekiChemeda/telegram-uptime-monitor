from sqlalchemy.future import select
from sqlalchemy import func
from app.database.connection import async_session
from app.models import CheckLog, Monitor
from datetime import datetime, timedelta, timezone

async def get_monitor_stats(monitor_id):
    async with async_session() as session:
        # Get Monitor
        monitor = await session.get(Monitor, monitor_id)
        if not monitor:
            return None

        # Calculate time ranges
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)

        # Count failures in last 24h
        q_24h = select(func.count(CheckLog.id)).where(
            CheckLog.monitor_id == monitor_id,
            CheckLog.is_up == False,
            CheckLog.checked_at >= one_day_ago
        )
        result_24h = await session.execute(q_24h)
        count_24h = result_24h.scalar()

        # Count failures in last 7d
        q_7d = select(func.count(CheckLog.id)).where(
            CheckLog.monitor_id == monitor_id,
            CheckLog.is_up == False,
            CheckLog.checked_at >= seven_days_ago
        )
        result_7d = await session.execute(q_7d)
        count_7d = result_7d.scalar()

        # Get last incident
        q_last_down = select(CheckLog).where(
            CheckLog.monitor_id == monitor_id,
            CheckLog.is_up == False
        ).order_by(CheckLog.checked_at.desc()).limit(1)
        
        result_last_down = await session.execute(q_last_down)
        last_down_log = result_last_down.scalars().first()
        last_down_time = last_down_log.checked_at if last_down_log else None

        return {
            "name": monitor.name,
            "url": monitor.url,
            "current_status": monitor.last_status,
            "last_checked": monitor.last_checked,
            "incidents_24h": count_24h,
            "incidents_7d": count_7d,
            "last_incident": last_down_time
        }
