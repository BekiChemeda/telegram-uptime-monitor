from dotenv import load_dotenv
import os

# Load .env file, overriding any existing environment variables
load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env file or environment variables")

if not TELEGRAM_BOT_TOKEN:
    # Warning instead of raising error to allow running without bot token for testing
    print("WARNING: TELEGRAM_BOT_TOKEN is not set.")

print(f"Loaded DATABASE_URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'INVALID'}")
