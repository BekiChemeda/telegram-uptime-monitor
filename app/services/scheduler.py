import asyncio
from app.services.monitor_service import check_all_monitors
import logging

logger = logging.getLogger(__name__)

async def start_scheduler():
    logger.info("Starting monitoring scheduler...")
    while True:
        try:
            await check_all_monitors()
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
        
        # Determine wait time. For checking intervals of 60s, wait 10s or 5s?
        # If we check every 10 seconds, we pick up monitors that are due.
        await asyncio.sleep(10) 
