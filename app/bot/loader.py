from telebot.async_telebot import AsyncTeleBot
from app.config import TELEGRAM_BOT_TOKEN
import logging

logger = logging.getLogger(__name__)

bot = None

if TELEGRAM_BOT_TOKEN:
    bot = AsyncTeleBot(TELEGRAM_BOT_TOKEN)
else:
    logger.warning("TELEGRAM_BOT_TOKEN not set. Bot features will be disabled.")
