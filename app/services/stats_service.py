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
        thirty_days_ago = now - timedelta(days=30)

        # Helper to calc uptime
        async def calc_uptime(since):
            q_total = select(func.count(CheckLog.id)).where(
                CheckLog.monitor_id == monitor_id,
                CheckLog.checked_at >= since
            )
            res_total = await session.execute(q_total)
            total = res_total.scalar() or 0

            if total == 0: return 100.0, 0

            q_down = select(func.count(CheckLog.id)).where(
                CheckLog.monitor_id == monitor_id,
                CheckLog.is_up == False,
                CheckLog.checked_at >= since
            )
            res_down = await session.execute(q_down)
            down = res_down.scalar() or 0

            return ((total - down) / total) * 100.0, down

        uptime_24h, incidents_24h = await calc_uptime(one_day_ago)
        uptime_7d, incidents_7d = await calc_uptime(seven_days_ago)
        uptime_30d, incidents_30d = await calc_uptime(thirty_days_ago)

        # Calc Average Latency (24h)
        q_avg_lat = select(func.avg(CheckLog.response_time)).where(
            CheckLog.monitor_id == monitor_id,
            CheckLog.checked_at >= one_day_ago,
            CheckLog.response_time.is_not(None)
        )
        res_avg_lat = await session.execute(q_avg_lat)
        avg_lat = res_avg_lat.scalar() or 0.0



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
            "incidents_24h": incidents_24h,
            "incidents_7d": incidents_7d,
            "incidents_30d": incidents_30d,
            "uptime_24h": uptime_24h,
            "uptime_7d": uptime_7d,
            "uptime_30d": uptime_30d,
            "avg_latency_24h": avg_lat,
            "last_incident": last_down_time
        }
