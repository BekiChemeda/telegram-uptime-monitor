from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Monitor

def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Add Site", callback_data="menu_add_site"),
        InlineKeyboardButton("📋 My Sites", callback_data="menu_my_sites"),
        InlineKeyboardButton("👤 My Account", callback_data="menu_account"),
        InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
    )
    return markup

def my_sites_menu(monitors: list[Monitor]):
    markup = InlineKeyboardMarkup(row_width=1)
    if not monitors:
        return None
    
    for m in monitors:
        status_icon = "🟢" if m.last_status else "🔴"
        if m.last_status is None: status_icon = "⚪"
        markup.add(InlineKeyboardButton(f"{status_icon} {m.name or m.url}", callback_data=f"site_{m.id}"))
    
    markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu"))
    return markup

def site_details_menu(monitor_id, url=None):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    if url:
        buttons.append(InlineKeyboardButton("🌍 Visit Site", url=url))
        
    buttons.extend([
        InlineKeyboardButton("📊 Statistics", callback_data=f"stats_{monitor_id}"),
        InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{monitor_id}"),
        InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{monitor_id}"),
        InlineKeyboardButton("🔙 Back to List", callback_data="menu_my_sites")
    ])
    
    markup.add(*buttons)
    return markup

def settings_menu(user_notification_enabled: bool):
    markup = InlineKeyboardMarkup(row_width=1)
    
    notif_text = "🔔 Notifications: ON" if user_notification_enabled else "🔕 Notifications: OFF"
    markup.add(InlineKeyboardButton(notif_text, callback_data="toggle_global_notif"))
    
    markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu"))
    return markup
