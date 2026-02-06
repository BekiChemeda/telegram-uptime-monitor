from telebot.async_telebot import AsyncTeleBot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app.bot.loader import bot
from app.bot import keyboards
from app.database.connection import async_session
from app.models import User, Monitor
from app.schemas.monitor import MonitorCreate
from app.services.stats_service import get_monitor_stats
from app.services.email_service import send_email
from app.config import ADMIN_IDS
import re
import uuid
import random            
from datetime import datetime, timedelta, timezone

# State Management
STATES = {}
STATE_WAITING_URL = 'WAITING_URL'
STATE_WAITING_NAME = 'WAITING_NAME'

STATE_WAITING_KEYWORD_INC = 'WAITING_KEYWORD_INC'
STATE_WAITING_MAX_LATENCY = 'WAITING_MAX_LATENCY'
STATE_WAITING_TIMEOUT = 'WAITING_TIMEOUT'
STATE_WAITING_STATUS = 'WAITING_STATUS'
STATE_WAITING_EMAIL = 'WAITING_EMAIL'
STATE_WAITING_VERIFICATION_CODE = 'WAITING_VERIFICATION_CODE'
STATE_WAITING_FEEDBACK = 'WAITING_FEEDBACK'

# Admin States
# STATE_BROADCAST_CONTENT = 'BROADCAST_CONTENT'
# STATE_BROADCAST_CONFIRM = 'BROADCAST_CONFIRM'
# STATE_SET_QUOTA_ID = 'SET_QUOTA_ID'
# STATE_SET_QUOTA_LIMIT = 'SET_QUOTA_LIMIT'
STATE_WAITING_TIMEOUT = 'WAITING_TIMEOUT'
STATE_WAITING_STATUS = 'WAITING_STATUS'
STATE_WAITING_EMAIL = 'WAITING_EMAIL'

# Helper to get user
async def get_or_create_user(telegram_id, username):
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        if not user:
            new_user = User(telegram_id=telegram_id, username=username)
            session.add(new_user)
            await session.commit()
            return new_user, True
        return user, False

# --- Command Handlers ---

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    telegram_id = message.from_user.id
    user, created = await get_or_create_user(telegram_id, message.from_user.username)
    
    text = (
        f"Welcome back, {message.from_user.first_name}! 👋\n"
        if not created else
        f"Welcome {message.from_user.first_name}! 👋\n"
        f"I am your Uptime Monitor Bot. 🤖\n"
    )
    text += "Use the menu below to manage your monitors."
    
    await bot.reply_to(message, text, reply_markup=keyboards.main_menu(), disable_web_page_preview=True)

@bot.message_handler(commands=['feedback'])
async def start_feedback_flow(message):
    STATES[message.from_user.id] = {'state': STATE_WAITING_FEEDBACK}
    prompt = (
        "I'd love to hear your thoughts.\n"
        "Please type a short message about what should improve (tap Cancel if you change your mind)."
    )
    await bot.reply_to(message, prompt, reply_markup=keyboards.cancel_button(), disable_web_page_preview=True)

@bot.message_handler(commands=['reply'])
async def admin_reply(message):
    if message.from_user.id not in ADMIN_IDS:
        await bot.reply_to(message, "This command is only for admins.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await bot.reply_to(message, "Usage: /reply <user_id> <message>")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await bot.reply_to(message, "User ID must be a number.")
        return

    reply_body = parts[2].strip()
    if not reply_body:
        await bot.reply_to(message, "Please include a message to send.")
        return

    try:
        await bot.send_message(target_id, f"Admin reply:\n{reply_body}", disable_web_page_preview=True)
        await bot.reply_to(message, "Sent!", disable_web_page_preview=True)
    except Exception as exc:
        await bot.reply_to(message, f"Could not deliver reply: {exc}", disable_web_page_preview=True)

# --- Menu Handlers ---

@bot.callback_query_handler(func=lambda call: call.data == "help_topics_main")
async def callback_help_topics(call):
    text = (
        "🤖 **Uptime Monitor Knowledge Base**\n\n"
        "Select a topic below to learn more about how I work:"
    )
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=keyboards.help_topics_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "help_latency")
async def callback_help_latency(call):
    text = (
        "⚡ **What is Latency?**\n\n"
        "Latency is the time it takes for your server to respond to our request. It's measured in seconds.\n\n"
        "**Why it matters:**\n"
        "A slow website frustrates users and hurts SEO. We track this so you can ensure your site is snappy!\n\n"
        "You can set a threshold (e.g. 2s) to get alerted if your site becomes slow."
    )
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode='Markdown', reply_markup=keyboards.help_topic_back())

@bot.callback_query_handler(func=lambda call: call.data == "help_keywords")
async def callback_help_keywords(call):
    text = (
        "🔍 **What are Keywords?**\n\n"
        "Sometimes a website loads (Status 200 OK) but shows a blank page or an error message.\n\n"
        "**Keyword Monitoring** checks for a specific word that MUST be on your page (e.g., 'Welcome' or 'Copyright').\n"
        "If the word is missing, we consider the site DOWN, even if the server responds."
    )
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode='Markdown', reply_markup=keyboards.help_topic_back())

@bot.callback_query_handler(func=lambda call: call.data == "help_status")
async def callback_help_status(call):
    text = (
        "🔢 **HTTP Status Codes**\n\n"
        "Web servers communicate with codes:\n"
        "• **200-299:** Success (OK) ✅\n"
        "• **300-399:** Redirects ➡️\n"
        "• **400-499:** Client Errors (Not Found) ⚠️\n"
        "• **500-599:** Server Errors (Crash) 🔴\n\n"
        "By default, we consider any 2xx code as UP. You can enforce a specific code (like 200) in settings."
    )
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode='Markdown', reply_markup=keyboards.help_topic_back())

@bot.callback_query_handler(func=lambda call: call.data == "help_ssl")
async def callback_help_ssl(call):
    text = (
        "🔒 **SSL Monitoring**\n\n"
        "SSL Certificates encrypt data and give you that green lock icon.\n\n"
        "They expire! If they do, users see a scary warning.\n"
        "We check your certificate expiry date and warn you before it runs out."
    )
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode='Markdown', reply_markup=keyboards.help_topic_back())
    
@bot.callback_query_handler(func=lambda call: call.data == "help_maintenance")
async def callback_help_maintenance(call):
    text = (
        "\ud83d\udd28 **Pause & Maintenance**\n\n"
        "Tap **⏸ Pause** on a monitor before scheduled deploys or maintenance. While paused, the scheduler skips checks and you will not receive downtime alerts."
        "\n\n"
        "**Best Practices**\n"
        "• Pause only a few minutes before your change window and resume once smoke tests pass.\n"
        "• Use descriptive monitor names so teammates know which service is offline.\n"
        "• Maintenance windows with automatic start/end times are on the roadmap, so you will be able to schedule them without manual pauses."
    )
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=keyboards.help_topic_back()
    )

@bot.callback_query_handler(func=lambda call: call.data == "help_notifications")
async def callback_help_notifications(call):
    text = (
        "\ud83d\udd14 **Alerts & Notifications**\n\n"
        "Telegram DMs fire whenever a monitor flips between UP and DOWN. Use **Settings → Telegram Notifications** to mute or re-enable global alerts.\n\n"
        "**Email Alerts**\n"
        "• Set up your address once, then toggle delivery per user.\n"
        "• Emails include the failing URL, reason, response time, and when the service recovered.\n\n"
        "**Coming Soon**\n"
        "• Slack / Discord webhooks for team chatrooms.\n"
        "• Pager-style escalation (notify teammate if you do not ACK)."
    )
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=keyboards.help_topic_back()
    )

@bot.callback_query_handler(func=lambda call: call.data == "help_about")
async def callback_help_about(call):
    text = (
        "About\n\n"
        "This bot watches your sites and lets you know when they slow down or go offline."
        " You can pause checks during maintenance and view simple uptime stats right inside Telegram."
        " If you need help or want to suggest a feature, send /feedback and an admin will reply."
    )
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=keyboards.help_topic_back()
    )

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
async def callback_main_menu(call):
    text = "Use the menu below to manage your monitors."
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=keyboards.main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "cancel_action")
async def callback_cancel(call):
    if call.from_user.id in STATES:
        del STATES[call.from_user.id]
    
    await bot.answer_callback_query(call.id, "Action cancelled.")
    await callback_main_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "menu_add_site")
async def callback_add_site(call):
    # Answer callback to stop loading animation
    await bot.answer_callback_query(call.id)
    
    # Set state
    STATES[call.from_user.id] = {'state': STATE_WAITING_URL}
    
    # Send prompt
    await bot.send_message(call.message.chat.id, "Please enter the URL of the website you want to monitor (e.g., https://google.com):", reply_markup=keyboards.cancel_button(), disable_web_page_preview=True)

@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_URL)
async def process_url_step(message):
    try:
        url = message.text.strip()
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url # Default to https
            
        # Update state with URL and move to next step
        STATES[message.from_user.id] = {'state': STATE_WAITING_NAME, 'url': url}
        
        await bot.reply_to(message, f"URL: {url}\n\nNow, give this monitor a short name (e.g., 'My Portfolio'):", reply_markup=keyboards.cancel_button(), disable_web_page_preview=True)
    except Exception as e:
        await bot.reply_to(message, f"An error occurred: {e}", disable_web_page_preview=True)
        # Clear state on error
        if message.from_user.id in STATES:
            del STATES[message.from_user.id]

@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_NAME)
async def process_name_step(message):
    try:
        user_id = message.from_user.id
        state_data = STATES.get(user_id)
        if not state_data:
            return # Should not happen given the filter
            
        url = state_data['url']
        name = message.text.strip()
        
        # database operations...
        telegram_id = message.from_user.id
        
        async with async_session() as session:
            result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
            user = result.scalars().first()
            
            # Check existing
            existing = await session.execute(select(Monitor).filter(Monitor.owner_id == user.id, Monitor.url == url))
            if existing.scalars().first():
                await bot.reply_to(message, "You are already monitoring this URL!", reply_markup=keyboards.main_menu(), disable_web_page_preview=True)
                del STATES[user_id]
                return
                
            new_monitor = Monitor(
                owner_id=user.id,
                url=url,
                name=name,
                interval_seconds=60, 
                is_active=True
            )
            session.add(new_monitor)
            await session.commit()
            
        await bot.reply_to(message, f"✅ Site Added!\nName: {name}\nURL: {url}", reply_markup=keyboards.main_menu(), disable_web_page_preview=True)
        
        # Clean up state
        del STATES[user_id]
        
    except Exception as e:
        await bot.reply_to(message, f"An error occurred: {e}", disable_web_page_preview=True)
        if message.from_user.id in STATES:
            del STATES[message.from_user.id]

@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_FEEDBACK)
async def process_feedback_step(message):
    user_id = message.from_user.id
    feedback_text = (message.text or "").strip()
    if not feedback_text:
        await bot.reply_to(message, "Please type a short message or tap Cancel.", disable_web_page_preview=True)
        return

    if user_id in STATES:
        del STATES[user_id]

    # Forward the message to all admins
    admin_delivered = False
    for admin_id in ADMIN_IDS:
        try:
            # Forward the user's original message
            await bot.forward_message(admin_id, user_id, message.message_id)
            
            # Send user info and reply instructions
            user_info = f"New feedback from user {user_id}"
            if message.from_user.username:
                user_info += f" (@{message.from_user.username})"
            
            reply_instruction = f"To reply, use: /reply {user_id} <your message>"
            
            await bot.send_message(admin_id, f"{user_info}\n{reply_instruction}")
            admin_delivered = True
        except Exception as e:
            print(f"Failed to forward feedback to admin {admin_id}: {e}")
            continue

    if admin_delivered:
        await bot.reply_to(message, "Thanks! Your feedback has been sent to the admins.", disable_web_page_preview=True)
    else:
        await bot.reply_to(message, "Thank you for your feedback! We've received it.", disable_web_page_preview=True)


# Note: menu_my_sites is handled by callback_back_to_list (should be renamed to callback_my_sites for clarity, but logic is same)
# We will use the existing callback handler for data='menu_my_sites'

@bot.callback_query_handler(func=lambda call: call.data == "menu_account")
async def callback_account(call):
    telegram_id = call.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        
        # Count monitors
        count_q = await session.execute(select(func.count(Monitor.id)).filter(Monitor.owner_id == user.id))
        count = count_q.scalar()
        
    # Formatting
    username = user.username.replace("_", "\\_") if user.username else "N/A"
    
    # Email Quota Logic
    email_limit = getattr(user, 'email_limit', 4)
    email_count = user.email_notification_count
    # Visual bar (capped at 10 for display purposes)
    display_limit = min(email_limit, 10)
    display_count = min(email_count, display_limit)
    remaining_bar = max(0, display_limit - display_count)
    email_bar = "▓" * display_count + "░" * remaining_bar
    
    text = (
        f"👤 **Account Dashboard**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 **User Profile**\n"
        f"🆔 **ID:** `{user.telegram_id}`\n"
        f"👤 **Handle:** @{username}\n"
        f"📅 **Member Since:** {user.joined_at.strftime('%b %d, %Y')}\n\n"
        
        f"📊 **Monitor Stats**\n"
        f"📡 **Total Monitors:** `{count}`\n"
        f"⏱ **Check Frequency:** `1 min`\n\n"
        
        f"📬 **Notification Quota**\n"
    )
    
    if user.is_email_notification_enabled and user.email:
        text += (
             f"📧 **Email:** `{user.email}`\n"
             f"📉 **Daily Usage:** `{email_count}/{email_limit}`\n"
             f"`[{email_bar}]`\n"
        )
    else:
        text += "❌ **Email Alerts:** Disabled\n_(Enable in Settings)_"

    # Edit the message instead of replying
    try:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu() 
        )
    except Exception as e:
        print(f"Error editing message (My Account): {e}")
        # Fallback without markdown if error (likely username char issue still)
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text.replace('*', '').replace('`', '').replace('_', ''),
            reply_markup=keyboards.main_menu()
        )
    
    await bot.answer_callback_query(call.id)
    # Add a "Back" button to the text via main_menu? 
    # The main_menu() returns the main buttons. 
    # If we are in "Account Info", we might want a "Back" button instead of the full menu immediately.
    # But for simplicity, let's show the content AND the main menu options below it, or just a Back button.
    # The user asked for navigation. Showing the main menu buttons again allows quick navigation.
    # However, standard practice is a "Back" button.
    # Let's adjust main_menu to be used only on root.
    # But wait, the previous code used `reply_markup=keyboards.main_menu()`.
    # Implementation: Text displayed is Account info, buttons below are Main Menu actions. This works as a "Tab" switch.

@bot.callback_query_handler(func=lambda call: call.data == "menu_settings")
async def callback_settings(call):
    telegram_id = call.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
    
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Global Settings:", 
        reply_markup=keyboards.settings_menu(user.is_notification_enabled, user.email, user.is_email_notification_enabled)
    )


# --- Callback Handlers ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('site_'))
async def callback_site_details(call):
    monitor_id_str = call.data.split('_')[1]
    monitor_id = uuid.UUID(monitor_id_str)
    
    stats = await get_monitor_stats(monitor_id)
    
    if not stats:
        await bot.answer_callback_query(call.id, "Monitor not found!")
        return
        
    status_emoji = "🟢 UP" if stats['current_status'] else "🔴 DOWN"
    # Fetch actual object to get is_active status
    async with async_session() as session:
        monitor = await session.get(Monitor, monitor_id)
        is_active = monitor.is_active

    if stats['current_status'] is None: status_emoji = "⚪ PENDING"
    if not is_active: status_emoji = "🟡 PAUSED" 
    
    text = (
        f"🌐 **{stats['name']}**\n"
        f"🔗 {stats['url']}\n\n"
        f"**Status:** {status_emoji}\n"
        f"**State:** {'▶️ Running' if is_active else '⏸ Paused'}\n"
        f"**Uptime (24h):** {stats['uptime_24h']:.2f}%\n"
        f"**Last Checked:** {stats['last_checked'].strftime('%Y-%m-%d %H:%M:%S UTC') if stats['last_checked'] else 'Never'}\n\n"
        f"**Incidents (24h):** {stats['incidents_24h']}\n"
        f"**Incidents (7d):** {stats['incidents_7d']}\n"
    )
    if stats['last_incident']:
         text += f"**Last Incident:** {stats['last_incident'].strftime('%Y-%m-%d %H:%M UTC')}\n"

    try:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboards.site_details_menu(monitor_id_str, stats['url'], is_active)
        )
    except Exception as e:
        # Sometimes editing fails if content is same
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith(('pause_', 'resume_')))
async def callback_toggle_pause(call):
    action, monitor_id_str = call.data.split('_')
    monitor_id = uuid.UUID(monitor_id_str)
    
    async with async_session() as session:
        monitor = await session.get(Monitor, monitor_id)
        if monitor:
            monitor.is_active = (action == 'resume')
            await session.commit()
            
            status_text = "Resumed" if action == 'resume' else "Paused"
            await bot.answer_callback_query(call.id, f"Monitor {status_text}!")
            
            # Redirect back to site details to refresh UI
            call.data = f"site_{monitor_id_str}"
            await callback_site_details(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_'))
async def callback_check_now(call):
    monitor_id_str = call.data.split('_')[1]
    monitor_id = uuid.UUID(monitor_id_str)
    
    await bot.answer_callback_query(call.id, "Running checks... Please wait ⏳")
    
    try:
        from app.services.monitor_service import check_single_monitor
        
        async with async_session() as session:
            monitor = await session.get(Monitor, monitor_id)
            if not monitor:
                return

            # Force check (bypass maintenance check logic?) - No, usually maintenance should still respect unless override
            # But user explicitly asked. Let's run it.
            # We need to eagerly load for notification logic inside check_single_monitor if needed
            # But check_single_monitor updates DB.
            
            # Re-fetch with relationships if needed by check_single_monitor logic (owner)
            # Actually check_single_monitor doesn't strictly require owner unless sending notification
            # But notification service needs owner.
            # So let's use selectinload
            stmt = select(Monitor).where(Monitor.id == monitor_id).options(selectinload(Monitor.owner), selectinload(Monitor.maintenance_windows))
            result = await session.execute(stmt)
            monitor_full = result.scalars().first()
            
            is_up = await check_single_monitor(monitor_full, session)
            await session.commit()
            
        emoji = "🟢 UP" if is_up else "🔴 DOWN"
        await bot.send_message(call.message.chat.id, f"Check Complete for {monitor_full.name}:\nResult: **{emoji}**", parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        await bot.send_message(call.message.chat.id, f"Error running check: {e}", disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stats_'))
async def callback_stats_menu(call):
    monitor_id_str = call.data.split('_')[1]
    monitor_id = uuid.UUID(monitor_id_str)
    
    stats = await get_monitor_stats(monitor_id)
    if not stats:
        await bot.answer_callback_query(call.id, "Monitor not found!")
        return
        
    text = (
        f"📊 **Extended Statistics: {stats['name']}**\n\n"
        f"**Uptime**\n"
        f"• 24h: {stats['uptime_24h']:.2f}%\n"
        f"• 7d:  {stats['uptime_7d']:.2f}%\n"
        f"• 30d: {stats['uptime_30d']:.2f}%\n\n"
        
        f"**Incidents**\n"
        f"• 24h: {stats['incidents_24h']}\n"
        f"• 7d:  {stats['incidents_7d']}\n"
        f"• 30d: {stats['incidents_30d']}\n\n"
        
        f"**Performance**\n"
        f"• Avg Latency (24h): {stats['avg_latency_24h']:.3f}s\n"
    )
    
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=keyboards.stats_view_menu(monitor_id_str)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_'))
async def callback_edit_monitor_menu(call):
    # This handles the root "edit_{id}" and sub-menus
    # e.g. edit_ssl_{id}, edit_{id}
    
    parts = call.data.split('_')
    action = parts[1] # 'ssl', 'kw', 'int' or uuid if it is just 'edit_uuid'
    
    # If len is 2, it's the main edit menu: edit_{uuid}
    if len(parts) == 2:
         monitor_id_str = parts[1]
         monitor_id = uuid.UUID(monitor_id_str)
         async with async_session() as session:
            monitor = await session.get(Monitor, monitor_id)
            if not monitor:
                await bot.answer_callback_query(call.id, "Monitor not found")
                return

            text = (
                f"⚙️ **Edit Monitor Settings**\n"
                f"**Name:** {monitor.name}\n"
                f"**URL:** {monitor.url}\n\n"
                f"Select a setting to change:"
            )
            
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=keyboards.monitor_edit_menu(monitor_id_str, monitor)
            )
            return

    # Sub-actions: edit_ssl_{uuid}, edit_kw_{uuid}, etc.
    sub_action = parts[1]
    monitor_id_str = parts[2]
    monitor_id = uuid.UUID(monitor_id_str)
    
    async with async_session() as session:
        monitor = await session.get(Monitor, monitor_id)
        if not monitor: return

        if sub_action == 'ssl':
            monitor.check_ssl = not monitor.check_ssl
            await session.commit()
            status = "enabled" if monitor.check_ssl else "disabled"
            await bot.answer_callback_query(call.id, f"SSL Check {status}")
            
            # Refresh menu
            await bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboards.monitor_edit_menu(monitor_id_str, monitor)
            )

        elif sub_action == 'kw':
            STATES[call.from_user.id] = {'state': STATE_WAITING_KEYWORD_INC, 'monitor_id': monitor_id_str}
            await bot.send_message(
                call.message.chat.id, 
                "**Keyword Monitoring**\n"
                "Enter a word or phrase that MUST be present on the page (Case Sensitive).\n"
                "Send `skip` to remove keyword checks.",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_button(),
                disable_web_page_preview=True
            )
            await bot.answer_callback_query(call.id)

        elif sub_action == 'lat':
            STATES[call.from_user.id] = {'state': STATE_WAITING_MAX_LATENCY, 'monitor_id': monitor_id_str}
            await bot.send_message(
                call.message.chat.id,
                "**Latency Threshold**\n"
                "Enter max seconds (e.g., `2.5`) before considering it 'Slow'.\n"
                "Send `0` to disable.",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_button(),
                disable_web_page_preview=True
            )
            await bot.answer_callback_query(call.id)
            
        elif sub_action == 'timeout':
            STATES[call.from_user.id] = {'state': STATE_WAITING_TIMEOUT, 'monitor_id': monitor_id_str}
            await bot.send_message(
                call.message.chat.id,
                "**Set Timeout**\n"
                "Enter max seconds to wait for a response (e.g. `10`, `30`).\n"
                "Default is 10s.",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_button(),
                disable_web_page_preview=True
            )
            await bot.answer_callback_query(call.id)

        elif sub_action == 'status':
            STATES[call.from_user.id] = {'state': STATE_WAITING_STATUS, 'monitor_id': monitor_id_str}
            await bot.send_message(
                call.message.chat.id,
                "**Expected Status Code**\n"
                "Enter the specific HTTP status code to expect (e.g., `201`, `301`).\n"
                "Send `0` to allow any 2xx.",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_button(),
                disable_web_page_preview=True
            )
            await bot.answer_callback_query(call.id)
            
@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_KEYWORD_INC)
async def process_keyword_step(message):
    try:
        user_id = message.from_user.id
        data = STATES.get(user_id)
        monitor_id = uuid.UUID(data['monitor_id'])
        text = message.text.strip()
        
        kw_inc = None if text.lower() == 'skip' else text
        
        async with async_session() as session:
            monitor = await session.get(Monitor, monitor_id)
            if monitor:
                monitor.keyword_include = kw_inc
                await session.commit()
                await bot.reply_to(message, "✅ Keyword settings updated!", disable_web_page_preview=True)
                
                # Show updated menu
                await bot.send_message(
                    message.chat.id,
                    f"Back to settings for {monitor.name}:",
                    reply_markup=keyboards.monitor_edit_menu(str(monitor_id), monitor),
                    disable_web_page_preview=True
                )

        del STATES[user_id]
    except Exception as e:
        await bot.reply_to(message, f"Error: {e}", disable_web_page_preview=True)

@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_MAX_LATENCY)
async def process_latency_step(message):
    try:
        user_id = message.from_user.id
        data = STATES.get(user_id)
        monitor_id = uuid.UUID(data['monitor_id'])
        
        val = float(message.text.strip())
        val = None if val <= 0 else val
        
        async with async_session() as session:
            monitor = await session.get(Monitor, monitor_id)
            if monitor:
                monitor.max_response_time = val
                await session.commit()
                await bot.reply_to(message, "✅ Latency threshold updated!", disable_web_page_preview=True)
                
                # Show updated menu
                await bot.send_message(
                    message.chat.id,
                    f"Back to settings for {monitor.name}:",
                    reply_markup=keyboards.monitor_edit_menu(str(monitor_id), monitor),
                    disable_web_page_preview=True
                )

        del STATES[user_id]
    except ValueError:
        await bot.reply_to(message, "Please enter a valid number (e.g. 1.5) or 0.", disable_web_page_preview=True)
    except Exception as e:
        await bot.reply_to(message, f"Error: {e}", disable_web_page_preview=True)

@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_TIMEOUT)
async def process_timeout_step(message):
    try:
        user_id = message.from_user.id
        data = STATES.get(user_id)
        monitor_id = uuid.UUID(data['monitor_id'])
        
        val = int(message.text.strip())
        if val < 1: raise ValueError
        
        async with async_session() as session:
            monitor = await session.get(Monitor, monitor_id)
            if monitor:
                monitor.timeout_seconds = val
                await session.commit()
                await bot.reply_to(message, "✅ Timeout updated!", disable_web_page_preview=True)
                await bot.send_message(message.chat.id, f"Back to settings for {monitor.name}:", reply_markup=keyboards.monitor_edit_menu(str(monitor_id), monitor), disable_web_page_preview=True)
        del STATES[user_id]
    except:
        await bot.reply_to(message, "Please enter a valid integer > 0.", disable_web_page_preview=True)

@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_STATUS)
async def process_status_step(message):
    try:
        user_id = message.from_user.id
        data = STATES.get(user_id)
        monitor_id = uuid.UUID(data['monitor_id'])
        
        val = int(message.text.strip())
        val = None if val == 0 else val
        
        async with async_session() as session:
            monitor = await session.get(Monitor, monitor_id)
            if monitor:
                monitor.expected_status = val
                await session.commit()
                await bot.reply_to(message, "✅ Expected Status updated!", disable_web_page_preview=True)
                await bot.send_message(message.chat.id, f"Back to settings for {monitor.name}:", reply_markup=keyboards.monitor_edit_menu(str(monitor_id), monitor), disable_web_page_preview=True)
        del STATES[user_id]
    except:
        await bot.reply_to(message, "Please enter a valid status code (e.g. 200) or 0.", disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data == "menu_my_sites")
async def callback_back_to_list(call):
    telegram_id = call.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        result_m = await session.execute(select(Monitor).filter(Monitor.owner_id == user.id))
        monitors = result_m.scalars().all()
    
    if not monitors:
        text = "You haven't added any sites yet."
        markup = keyboards.main_menu() # Go back to main menu options
    else:
        text = "Your Monitored Sites:"
        markup = keyboards.my_sites_menu(monitors)
        # We need to ensure my_sites_menu returns a markup that allows going back?
        # my_sites_menu handles list. Does it have a "Back" button?
        # Let's check keyboards.py

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
async def callback_delete_monitor(call):
    monitor_id_str = call.data.split('_')[1]
    monitor_id = uuid.UUID(monitor_id_str)
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🚫 Cancel", callback_data=f"site_{monitor_id_str}"),
        InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_del_{monitor_id_str}")
    )
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="⚠️ **Are you sure you want to delete this monitor?**\nThis action cannot be undone.",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
async def callback_confirm_delete_monitor(call):
    monitor_id_str = call.data.split('_')[2] # confirm_del_UUID
    monitor_id = uuid.UUID(monitor_id_str)
    
    async with async_session() as session:
        monitor = await session.get(Monitor, monitor_id)
        if monitor:
            await session.delete(monitor)
            await session.commit()
            
    await bot.answer_callback_query(call.id, "Monitor deleted.")
    await callback_back_to_list(call)

@bot.callback_query_handler(func=lambda call: call.data == "toggle_global_notif")
async def callback_toggle_notif(call):
    telegram_id = call.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        user.is_notification_enabled = not user.is_notification_enabled
        new_state = user.is_notification_enabled
        await session.commit()
    
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.settings_menu(new_state, user.email, user.is_email_notification_enabled)
    )
    status = "ON" if new_state else "OFF"
    await bot.answer_callback_query(call.id, f"Notifications turned {status}")

@bot.callback_query_handler(func=lambda call: call.data == "setup_email")
async def callback_setup_email(call):
    STATES[call.from_user.id] = {'state': STATE_WAITING_EMAIL}
    await bot.send_message(call.message.chat.id, "📧 Please reply with your email address:", reply_markup=keyboards.cancel_button(), disable_web_page_preview=True)
    await bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_email_setup")
async def callback_back_to_email(call):
    STATES[call.from_user.id] = {'state': STATE_WAITING_EMAIL}
    
    # We edit the message to prompt for email again
    await bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id, 
        text="📧 Please reply with your email address:", 
        reply_markup=keyboards.cancel_button()
    )
    await bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_EMAIL)
async def process_email_step(message):
    email = message.text.strip()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await bot.reply_to(message, "Invalid email format. Please try again.", disable_web_page_preview=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == message.from_user.id))
        user = result.scalars().first()
        
        # Check Verification Quota
        now = datetime.now(timezone.utc)
        if user.last_verification_attempt_date:
             if user.last_verification_attempt_date.date() < now.date():
                 user.verification_attempts_count = 0
        
        if user.verification_attempts_count >= 2:
            await bot.reply_to(message, "❌ You have reached the maximum of 2 verification attempts for today. Please try again tomorrow.", disable_web_page_preview=True)
            del STATES[message.from_user.id]
            return

        # Generate Code
        code = str(random.randint(100000, 999999))
        
        # Update User
        user.email = email
        user.is_email_notification_enabled = False # Disable until verified
        user.is_email_verified = False
        user.email_verification_code = code
        user.email_verification_expiry = now + timedelta(minutes=15)
        user.verification_attempts_count += 1
        user.last_verification_attempt_date = now
        await session.commit()
    
    # Send Email
    subject = "Verify your email for Telegram Uptime Monitor"
    html_content = f"<h2>Verification Code</h2><p>Your code is: <strong>{code}</strong></p><p>Expires in 15 minutes.</p>"
    
    await bot.send_message(message.chat.id, "⏳ Sending verification email...", disable_web_page_preview=True)
    sent = await send_email(email, subject, html_content)
    
    if sent:
        STATES[message.from_user.id] = {'state': STATE_WAITING_VERIFICATION_CODE}
        await bot.reply_to(message, f"📨 A verification code has been sent to {email}.\n\nPlease enter the 6-digit code here to verify:", reply_markup=keyboards.verification_code_menu(), disable_web_page_preview=True)
    else:
        await bot.reply_to(message, "❌ Failed to send verification email. Please check the address and try again.", disable_web_page_preview=True)
        del STATES[message.from_user.id]

@bot.message_handler(func=lambda msg: STATES.get(msg.from_user.id, {}).get('state') == STATE_WAITING_VERIFICATION_CODE)
async def process_verification_code_step(message):
    code = message.text.strip()
    if not code.isdigit() or len(code) != 6:
        await bot.reply_to(message, "Invalid format. Please enter the 6-digit code.", disable_web_page_preview=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == message.from_user.id))
        user = result.scalars().first()
        
        now = datetime.now(timezone.utc)
        
        # Handle case where user might check verification but code is missing
        if not user.email_verification_code:
             await bot.reply_to(message, "No pending verification found. Please set email again.", disable_web_page_preview=True)
             del STATES[message.from_user.id]
             return
             
        if user.email_verification_expiry.replace(tzinfo=timezone.utc) < now:
             await bot.reply_to(message, "❌ Code expired. Please start over.", disable_web_page_preview=True)
             del STATES[message.from_user.id]
             return
             
        if user.email_verification_code == code:
            user.is_email_verified = True
            user.is_email_notification_enabled = True
            user.email_verification_code = None # clear
            await session.commit()
            
            await bot.reply_to(message, "✅ Email Verified! Notifications are now ON.", disable_web_page_preview=True)
            del STATES[message.from_user.id]
        else:
            await bot.reply_to(message, "❌ Incorrect code. Please try again.", disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data == "config_email")
async def callback_config_email(call):
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == call.from_user.id))
        user = result.scalars().first()
        
        if not user.is_email_verified and user.email:
             status_display = "⚠️ Unverified"
        else:
             status_display = "✅ ON" if user.is_email_notification_enabled else "❌ OFF"
             
        count = user.email_notification_count

    markup = InlineKeyboardMarkup()
    
    if user.is_email_verified:
        markup.add(
            InlineKeyboardButton(f"Toggle: {status_display}", callback_data="toggle_email"),
            InlineKeyboardButton("✏️ Change Email", callback_data="setup_email"),
            InlineKeyboardButton("🔙 Back", callback_data="menu_settings")
        )
    else:
        markup.add(
            InlineKeyboardButton("✏️ Verify / Change Email", callback_data="setup_email"),
            InlineKeyboardButton("🔙 Back", callback_data="menu_settings")
        )
    
    text = (
        f"📧 **Email Settings**\n"
        f"**Email:** {user.email}\n"
        f"**Status:** {status_display}\n"
        f"**Sent Today:** {count}/{getattr(user, 'email_limit', 10)}"
    )
    
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "toggle_email")
async def callback_toggle_email(call):
    telegram_id = call.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        user.is_email_notification_enabled = not user.is_email_notification_enabled
        state = "ON" if user.is_email_notification_enabled else "OFF"
        await session.commit()
        
    await bot.answer_callback_query(call.id, f"Email Notifications: {state}")
    await callback_config_email(call)


