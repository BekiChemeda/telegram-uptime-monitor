from app.models import Monitor
from app.bot.loader import bot
import logging

logger = logging.getLogger(__name__)

async def send_notification(monitor: Monitor, previous_status: bool, current_status: bool):
    """
    Sends a notification via Telegram about the status change.
    """
    if not bot:
        logger.warning("Bot is not initialized. Skipping notification.")
        return

    user = monitor.owner
    if not user or not user.telegram_id:
        logger.warning(f"Monitor {monitor.id} has no owner with telegram_id. Skipping.")
        return

    status_str = "UP 🟢" if current_status else "DOWN 🔴"
    prev_str = "UP" if previous_status else "DOWN"
    
    emoji = "✅" if current_status else "🚨"
    
    message = (
        f"{emoji} **Monitor Status Change**\n\n"
        f"**Name:** {monitor.name or 'Unnamed'}\n"
        f"**URL:** {monitor.url}\n"
        f"**Status:** {prev_str} -> **{status_str}**\n"
        f"**Time:** {monitor.last_checked.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"Notification sent to {user.telegram_id} for monitor {monitor.id}")
    except Exception as e:
        logger.error(f"Failed to send notification to {user.telegram_id}: {e}")
