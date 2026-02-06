from dotenv import load_dotenv
import os
from pathlib import Path
import logging
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

logger = logging.getLogger(__name__)

# Explicitly find the .env file in the project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def _ensure_asyncpg_scheme(url: str) -> str:
    """Render/Postgres defaults to postgres://; upgrade to async driver automatically."""
    if not url:
        return url
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _normalize_query_params(url: str) -> str:
    """Translate provider-specific query params to asyncpg-friendly flags."""
    if not url:
        return url
    parsed = urlparse(url)
    if not parsed.query:
        return url
    updated = False
    new_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered == "sslmode":
            updated = True
            normalized = value.lower()
            if normalized in {"require", "verify-full", "verify-ca"}:
                new_pairs.append(("ssl", "true"))
            elif normalized == "disable":
                new_pairs.append(("ssl", "false"))
            else:
                new_pairs.append(("ssl", value))
        elif lowered == "channel_binding":
            updated = True
            if value.lower() not in {"prefer", "disable"}:
                logger.warning(
                    "Removing unsupported channel_binding=%s from DATABASE_URL for asyncpg",
                    value,
                )
            # asyncpg does not accept channel_binding kwarg, so drop it entirely
            continue
        else:
            new_pairs.append((key, value))
    if not updated:
        return url
    new_query = urlencode(new_pairs)
    return urlunparse(parsed._replace(query=new_query))


DATABASE_URL_RAW = os.getenv("DATABASE_URL")
DATABASE_URL = _normalize_query_params(_ensure_asyncpg_scheme(DATABASE_URL_RAW))
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
