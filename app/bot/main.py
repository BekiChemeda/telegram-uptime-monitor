import asyncio
from app.bot.loader import bot
import app.bot.handlers # Register handlers logic
import logging

logger = logging.getLogger(__name__)

async def start_bot():
    if not bot:
        logger.warning("Bot token not set, skipping bot startup.")
        return

    logger.info("Starting Telegram Bot Polling...")
    # remove webhook before polling if it was set
    # await bot.remove_webhook() 
    
    try:
        await bot.infinity_polling(logger_level=logging.INFO)
    except Exception as e:
        logger.error(f"Bot polling failed: {e}")
