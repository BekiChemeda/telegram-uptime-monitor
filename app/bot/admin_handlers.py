from telebot.async_telebot import AsyncTeleBot
from telebot import types
from sqlalchemy.future import select
from sqlalchemy import func
from app.bot.loader import bot
from app.bot import keyboards
from app.database.connection import async_session
from app.models import User, Monitor
from app.config import ADMIN_IDS

# State Management for admin actions
STATES = {}
STATE_BROADCAST_CONTENT = 'BROADCAST_CONTENT'
STATE_BROADCAST_CONFIRM = 'BROADCAST_CONFIRM'
STATE_SET_QUOTA_ID = 'SET_QUOTA_ID'
STATE_SET_QUOTA_LIMIT = 'SET_QUOTA_LIMIT'

@bot.message_handler(commands=['admin'])
async def admin_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await bot.reply_to(message, "🔐 **Admin Panel**", reply_markup=keyboards.admin_menu(), disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data == "admin_menu")
async def callback_admin_menu(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🔐 **Admin Panel**",
        parse_mode='Markdown',
        reply_markup=keyboards.admin_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
async def callback_admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    async with async_session() as session:
        user_count = await session.scalar(select(func.count(User.id)))
        monitor_count = await session.scalar(select(func.count(Monitor.id)))
        active_monitors = await session.scalar(select(func.count(Monitor.id)).filter(Monitor.is_active == True))
        
        # Count users with at least one monitor
        users_with_monitors = await session.scalar(
            select(func.count(func.distinct(Monitor.owner_id)))
        )

    text = (
        "📊 **System Statistics**\n\n"
        f"👥 **Total Users:** `{user_count}`\n"
        f"🙋‍♂️ **Users with Monitors:** `{users_with_monitors}`\n"
        f"📈 **Total Monitors:** `{monitor_count}`\n"
        f"✅ **Active Monitors:** `{active_monitors}`"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_menu"))

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
async def callback_admin_broadcast(call):
    if call.from_user.id not in ADMIN_IDS:
        return
        
    STATES[call.from_user.id] = {'state': STATE_BROADCAST_CONTENT}
    
    markup = keyboards.cancel_button()
    
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📢 **Broadcast Message**\n\nPlease send the message (text or photo with caption) you want to broadcast to all users.",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: STATES.get(m.from_user.id, {}).get('state') == STATE_BROADCAST_CONTENT, content_types=['text', 'photo'])
async def handler_broadcast_content(message):
    user_id = message.from_user.id
    
    is_forward = message.forward_date is not None

    content = {
        'type': 'forward' if is_forward else ('text' if message.text else 'photo'),
        'text': message.text or message.caption,
        'file_id': message.photo[-1].file_id if message.photo else None,
        'message_id': message.message_id,
        'from_chat_id': message.chat.id
    }
    STATES[user_id]['broadcast_content'] = content
    STATES[user_id]['state'] = STATE_BROADCAST_CONFIRM
    
    if content['type'] == 'forward':
        await bot.forward_message(message.chat.id, content['from_chat_id'], content['message_id'])
    elif content['type'] == 'photo':
        await bot.send_photo(message.chat.id, content['file_id'], caption=content['text'], disable_web_page_preview=True)
    else:
        await bot.send_message(message.chat.id, content['text'], disable_web_page_preview=True)

    await bot.send_message(
        message.chat.id, 
        "Do you want to send this message?", 
        parse_mode='Markdown',
        reply_markup=keyboards.admin_broadcast_menu(),
        disable_web_page_preview=True
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("broadcast_confirm_"))
async def callback_broadcast_confirm(call):
    if call.from_user.id not in ADMIN_IDS:
        return
        
    action = call.data.split("_")[2]
    user_id = call.from_user.id
    
    if action == "no":
        STATES[user_id] = {}
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await bot.send_message(call.message.chat.id, "❌ Broadcast cancelled.", reply_markup=keyboards.admin_menu(), disable_web_page_preview=True)
        return

    content = STATES.get(user_id, {}).get('broadcast_content')
    if not content:
        await bot.answer_callback_query(call.id, "Error: No content found.")
        return

    msg = await bot.send_message(call.message.chat.id, "⏳ Sending broadcast...", disable_web_page_preview=True)
    
    success_count = 0
    fail_count = 0
    
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        users = result.scalars().all()
        
        for uid in users:
            try:
                if content.get('type') == 'forward':
                    await bot.forward_message(uid, content['from_chat_id'], content['message_id'])
                elif content['type'] == 'photo':
                    await bot.send_photo(uid, content['file_id'], caption=content['text'], disable_web_page_preview=True)
                else:
                    await bot.send_message(uid, content['text'], disable_web_page_preview=True)
                success_count += 1
            except Exception as e:
                fail_count += 1
                
    result_text = (
        f"✅ **Broadcast Completed**\n\n"
        f"📨 Sent: `{success_count}`\n"
        f"❌ Failed: `{fail_count}`"
    )
    
    await bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=msg.message_id, 
        text=result_text, 
        parse_mode='Markdown',
        reply_markup=keyboards.admin_menu()
    )
    STATES[user_id] = {}


@bot.callback_query_handler(func=lambda call: call.data == "admin_quotas")
async def callback_admin_quotas(call):
    if call.from_user.id not in ADMIN_IDS:
        return
        
    STATES[call.from_user.id] = {'state': STATE_SET_QUOTA_ID}
    
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🔢 **Manage Quotas**\n\nPlease send the **Telegram ID** of the user you want to manage.",
        parse_mode='Markdown',
        reply_markup=keyboards.cancel_button()
    )

@bot.message_handler(func=lambda m: STATES.get(m.from_user.id, {}).get('state') == STATE_SET_QUOTA_ID)
async def handler_quota_id(message):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await bot.reply_to(message, "⚠️ Please enter a valid numeric Telegram ID.")
        return

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == target_id))
        user = result.scalars().first()
        
        if not user:
             await bot.reply_to(message, "⚠️ User not found in database.")
             return
             
        STATES[message.from_user.id]['target_user_id'] = target_id
        STATES[message.from_user.id]['state'] = STATE_SET_QUOTA_LIMIT

        limit = getattr(user, 'email_limit', 4)

        text = (
            f"👤 **User Found**\n"
            f"ID: `{user.telegram_id}`\n"
            f"Name: {user.username or 'No Username'}\n"
            f"Current Quota: `{user.email_notification_count}/{limit}` (Daily)\n\n"
            "✏️ **Enter new daily email limit (0-100):**"
        )
        await bot.reply_to(message, text, reply_markup=keyboards.cancel_button(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: STATES.get(m.from_user.id, {}).get('state') == STATE_SET_QUOTA_LIMIT)
async def handler_quota_limit(message):
    try:
        new_limit = int(message.text.strip())
        if new_limit < 0 or new_limit > 100:
             raise ValueError
    except ValueError:
        await bot.reply_to(message, "⚠️ Please enter a valid number (0-100).")
        return
        
    target_id = STATES[message.from_user.id].get('target_user_id')
    
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.telegram_id == target_id))
        user = result.scalars().first()
        
        if user:
            user.email_limit = new_limit
            await session.commit()
            await bot.reply_to(message, f"✅ Updated quota for user `{target_id}` to `{new_limit}` emails/day.", reply_markup=keyboards.admin_menu())
        else:
            await bot.reply_to(message, "⚠️ User not found.", reply_markup=keyboards.admin_menu())
            
    STATES[message.from_user.id] = {}
