from telebot.async_telebot import AsyncTeleBot
from telebot import types
from sqlalchemy.future import select
from sqlalchemy import func
from app.bot.loader import bot
from app.bot import keyboards
from app.database.connection import async_session
from app.models import User, Monitor
from app.schemas.monitor import MonitorCreate
from app.services.stats_service import get_monitor_stats
import re
import uuid

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
    
    await bot.reply_to(message, text, reply_markup=keyboards.main_menu())

# --- Text Menu Handlers ---

@bot.message_handler(func=lambda msg: msg.text == "➕ Add Site")
async def menu_add_site(message):
    await bot.reply_to(message, "Please enter the URL of the website you want to monitor (e.g., https://google.com):")
    bot.register_next_step_handler(message, process_url_step)

async def process_url_step(message):
    url = message.text.strip()
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url # Default to https
        
    # We could ask for name next, or just save it. User asked for "Add Site... lists buttons...".
    # Let's ask for name to be polite.
    await bot.reply_to(message, f"URL: {url}\n\nNow, give this monitor a short name (e.g., 'My Portfolio'):")
    bot.register_next_step_handler(message, process_name_step, url)

async def process_name_step(message, url):
    name = message.text.strip()
    telegram_id = message.from_user.id
    
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        
        # Check existing
        existing = await session.execute(select(Monitor).filter(Monitor.owner_id == user.id, Monitor.url == url))
        if existing.scalars().first():
            await bot.reply_to(message, "You are already monitoring this URL!", reply_markup=keyboards.main_menu())
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
        
    await bot.reply_to(message, f"✅ Site Added!\nName: {name}\nURL: {url}", reply_markup=keyboards.main_menu())

@bot.message_handler(func=lambda msg: msg.text == "📋 My Sites")
async def menu_my_sites(message):
    telegram_id = message.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        result_m = await session.execute(select(Monitor).filter(Monitor.owner_id == user.id))
        monitors = result_m.scalars().all()
        
    if not monitors:
        await bot.reply_to(message, "You haven't added any sites yet.", reply_markup=keyboards.main_menu())
    else:
        await bot.reply_to(
            message, 
            "Your Monitored Sites:", 
            reply_markup=keyboards.my_sites_menu(monitors)
        )

@bot.message_handler(func=lambda msg: msg.text == "👤 My Account")
async def menu_account(message):
    telegram_id = message.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        
        # Count monitors
        count_q = await session.execute(select(func.count(Monitor.id)).filter(Monitor.owner_id == user.id))
        count = count_q.scalar()
        
    text = (
        f"👤 **Account Info**\n\n"
        f"**Username:** @{user.username}\n"
        f"**Joined:** {user.joined_at.strftime('%Y-%m-%d')}\n"
        f"**Total Monitors:** {count}\n"
    )
    await bot.reply_to(message, text, parse_mode='Markdown', reply_markup=keyboards.main_menu())

@bot.message_handler(func=lambda msg: msg.text == "⚙️ Settings")
async def menu_settings(message):
    telegram_id = message.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
    
    await bot.reply_to(
        message, 
        "Global Settings:", 
        reply_markup=keyboards.settings_menu(user.is_notification_enabled)
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
    if stats['current_status'] is None: status_emoji = "⚪ PENDING"
    
    text = (
        f"🌐 **{stats['name']}**\n"
        f"🔗 {stats['url']}\n\n"
        f"**Status:** {status_emoji}\n"
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
            reply_markup=keyboards.site_details_menu(monitor_id_str)
        )
    except Exception as e:
        # Sometimes editing fails if content is same
        pass

@bot.callback_query_handler(func=lambda call: call.data == "menu_my_sites")
async def callback_back_to_list(call):
    # Reuse logic from menu_my_sites but edit message instead of reply
    telegram_id = call.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        result_m = await session.execute(select(Monitor).filter(Monitor.owner_id == user.id))
        monitors = result_m.scalars().all()
    
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Your Monitored Sites:",
        reply_markup=keyboards.my_sites_menu(monitors)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
async def callback_delete_monitor(call):
    monitor_id_str = call.data.split('_')[1]
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
        reply_markup=keyboards.settings_menu(new_state)
    )
    status = "ON" if new_state else "OFF"
    await bot.answer_callback_query(call.id, f"Notifications turned {status}")


@bot.callback_query_handler(func=lambda call: call.data == "close_settings")
async def callback_close(call):
    await bot.delete_message(call.message.chat.id, call.message.message_id)


