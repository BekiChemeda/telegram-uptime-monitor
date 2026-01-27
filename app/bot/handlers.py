from telebot.async_telebot import AsyncTeleBot
from telebot import types
from sqlalchemy.future import select
from app.bot.loader import bot
from app.database.connection import async_session
from app.models import User, Monitor
from app.schemas.monitor import MonitorCreate
import re

async def register_user(message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        
        if not user:
            new_user = User(telegram_id=telegram_id, username=username)
            session.add(new_user)
            await session.commit()
            return True # Created
        return False # Existed

@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
    telegram_id = message.from_user.id
    created = await register_user(message)
    
    text = (
        f"Welcome {message.from_user.first_name}! 👋\n"
        f"I am your Uptime Monitor Bot. 🤖\n\n"
        f"Commands:\n"
        f"/add <url> - Add a new monitor\n"
        f"/list - List your monitors\n"
        f"/del <id> - Delete a monitor (get ID from /list)\n"
    )
    if created:
        text += "\nChecked into the system! ✅"
        
    await bot.reply_to(message, text)

@bot.message_handler(commands=['add'])
async def add_monitor(message):
    # Format: /add https://google.com [interval]
    parts = message.text.split()
    if len(parts) < 2:
        await bot.reply_to(message, "Usage: /add <url> [name]")
        return
    
    url = parts[1]
    name = parts[2] if len(parts) > 2 else url
    
    # URL Validation (Basic)
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    telegram_id = message.from_user.id
    
    async with async_session() as session:
        # Get User
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        if not user:
            await bot.reply_to(message, "Please start the bot first with /start")
            return

        # Check existing
        result = await session.execute(select(Monitor).filter(Monitor.owner_id == user.id, Monitor.url == url))
        if result.scalars().first():
            await bot.reply_to(message, "You are already monitoring this URL.")
            return

        new_monitor = Monitor(
            owner_id=user.id,
            url=url,
            name=name,
            interval_seconds=60,
            timeout_seconds=10,
            expected_status=200,
            is_active=True
        )
        session.add(new_monitor)
        await session.commit()
        
    await bot.reply_to(message, f"Monitor added! 🚀\nURL: {url}\nInterval: 60s")

@bot.message_handler(commands=['list'])
async def list_monitors(message):
    telegram_id = message.from_user.id
    
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        if not user:
             await bot.reply_to(message, "Please start the bot first with /start")
             return
             
        result = await session.execute(select(Monitor).filter(Monitor.owner_id == user.id))
        monitors = result.scalars().all()
        
        if not monitors:
            await bot.reply_to(message, "You have no monitors. Add one with /add")
            return
            
        text = "YOUR MONITORS: 📋\n\n"
        for m in monitors:
            status = "🟢 UP" if m.last_status else "🔴 DOWN"
            if m.last_status is None: status = "⚪ PENDING"
            
            # Escape markdown special chars if needed, or use simple concatenation
            text += f"ID: `{m.id}`\nName: {m.name}\nURL: {m.url}\nStatus: {status}\nLast Check: {m.last_checked}\n\n"
            
        await bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['del'])
async def delete_monitor(message):
    parts = message.text.split()
    if len(parts) < 2:
        await bot.reply_to(message, "Usage: /del <monitor_id>")
        return
    
    monitor_id_str = parts[1]
    telegram_id = message.from_user.id
    
    async with async_session() as session:
        # Verify ownership
        # Need to join or 2 queries.
        # Simplest: Get monitor, check owner
        
        # UUID parsing
        try:
            import uuid
            m_uuid = uuid.UUID(monitor_id_str)
        except ValueError:
             await bot.reply_to(message, "Invalid ID format.")
             return

        result = await session.execute(select(Monitor).filter(Monitor.id == m_uuid))
        monitor = result.scalars().first()
        
        if not monitor:
            await bot.reply_to(message, "Monitor not found.")
            return
            
        # Get user to check ID
        result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
        user = result.scalars().first()
        
        if not user or monitor.owner_id != user.id:
            await bot.reply_to(message, "You are not authorized to delete this monitor.")
            return

        await session.delete(monitor)
        await session.commit()
    
    await bot.reply_to(message, "Monitor deleted. 🗑️")

