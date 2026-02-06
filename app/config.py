from dotenv import load_dotenv
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Explicitly find the .env file in the project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
API_ACCESS_TOKEN = os.getenv("API_ACCESS_TOKEN")

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")

DB_ECHO = os.getenv("DB_ECHO", "false").lower() in {"1", "true", "yes", "on"}

# Admin Config
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env file or environment variables")

if not TELEGRAM_BOT_TOKEN:
    # Warning instead of raising error to allow running without bot token for testing
    logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot features disabled.")

if not API_ACCESS_TOKEN:
    raise ValueError("API_ACCESS_TOKEN must be set before running the API server")
