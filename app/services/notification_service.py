from app.models import Monitor
from app.bot.loader import bot
from app.services.email_service import send_email
from app.database.connection import async_session
from app.config import BOT_USERNAME
from datetime import datetime, timezone
import logging
from telebot import types

logger = logging.getLogger(__name__)

async def send_notification(monitor: Monitor, previous_status: bool, current_status: bool, error_details: str = None):
    """
    Sends a notification via Telegram and Email about the status change.
    """
    if not bot:
        logger.warning("Bot is not initialized. Skipping notification.")
        return

    user = monitor.owner
    if not user:
        logger.warning(f"Monitor {monitor.id} has no owner. Skipping.")
        return

    status_str = "UP 🟢" if current_status else "DOWN 🔴"
    prev_str = "UP" if previous_status else "DOWN"
    
    emoji = "✅" if current_status else "🚨"
    
    error_section = ""
    if error_details and not current_status:
        error_section = f"\nError: {error_details}\n"

    button_url = f"https://t.me/{BOT_USERNAME}?start=start" if BOT_USERNAME else "https://t.me/"

    message = (
        f"{emoji} Monitor Status Change\n\n"
        f"Name: {monitor.name or 'Unnamed'}\n"
        f"URL: {monitor.url}\n"
        f"Status: {prev_str} -> {status_str}\n"
        f"{error_section}"
        f"Time: {monitor.last_checked.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    try:
        reply_markup = types.InlineKeyboardMarkup()
        reply_markup.add(types.InlineKeyboardButton("Open Bot", url=button_url))
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=reply_markup
        )
        logger.info(f"Notification sent to {user.telegram_id} for monitor {monitor.id}")
    except Exception as e:
        logger.error(f"Failed to send notification to {user.telegram_id}: {e}")

    # --- Email Notification Logic ---
    if user.is_email_notification_enabled and user.email:
        # Check rate limits
        now = datetime.now(timezone.utc)
        
        # Reset if day changed
        if user.last_email_notification_date:
            if user.last_email_notification_date.date() < now.date():
                user.email_notification_count = 0
        
        limit = getattr(user, 'email_limit', 10) # Default to 10
        
        if user.email_notification_count < limit:
            # Send Email
            # Construct HTML
            bg_color = "#d4edda" if current_status else "#f8d7da"
            text_color = "#155724" if current_status else "#721c24"
            
            html_body = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: {text_color};">Monitor Status Change</h2>
                <p><strong>Monitor:</strong> {monitor.name or 'Unnamed'}</p>
                <p><strong>URL:</strong> <a href="{monitor.url}">{monitor.url}</a></p>
                <p style="background-color: {bg_color}; padding: 10px; border-radius: 3px; color: {text_color};">
                    <strong>Status:</strong> {status_str}
                </p>
                {'<p><strong>Error:</strong> ' + error_details + '</p>' if error_details and not current_status else ''}
                <p>Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <hr>
                <p style="font-size: 12px; color: #888;">You are receiving this because you enabled email notifications. (Limit: {limit}/day)</p>
            </div>
            """
            
            email_sent = await send_email(
                to_email=user.email,
                subject=f"Monitor Alert: {monitor.name} is {prev_str} -> {status_str.split()[0]}",
                html_content=html_body
            )
            
            if email_sent:
                user.email_notification_count += 1
                user.last_email_notification_date = now
                logger.info(f"Email sent to {user.email}. Count today: {user.email_notification_count}")
        else:
            logger.info(f"Email limit reached for {user.email} ({user.email_notification_count}/{limit}). Skipping.")
