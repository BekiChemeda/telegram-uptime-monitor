from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Monitor

def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    # Row 1: Primary Actions
    markup.add(
        InlineKeyboardButton("➕ Add Site", callback_data="menu_add_site"),
        InlineKeyboardButton("📋 My Sites", callback_data="menu_my_sites")
    )
    # Row 2: Secondary / Config
    markup.add(
        InlineKeyboardButton("👤 Account", callback_data="menu_account"),
        InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
    )
    # Row 3: Support / Help (Expansion)
    markup.add(
        InlineKeyboardButton("❓ Help / Status", callback_data="help_topics_main")
    )
    return markup


def help_topics_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("What is Latency?", callback_data="help_latency"),
        InlineKeyboardButton("What are Keywords?", callback_data="help_keywords")
    )
    markup.add(
        InlineKeyboardButton("Status Codes?", callback_data="help_status"),
        InlineKeyboardButton("SSL Monitoring", callback_data="help_ssl")
    )
    markup.add(
        InlineKeyboardButton("Pause & Maintenance", callback_data="help_maintenance"),
        InlineKeyboardButton("Alerts & Notifications", callback_data="help_notifications")
    )
    markup.add(
        InlineKeyboardButton("About", callback_data="help_about")
    )
    markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu"))
    return markup

def help_topic_back():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back to Help", callback_data="help_topics_main"))
    return markup

def my_sites_menu(monitors: list[Monitor]):
    markup = InlineKeyboardMarkup(row_width=1)
    if not monitors:
        return None
    
    for m in monitors:
        if not m.is_active:
             status_icon = "🟡" # Paused
        elif m.last_status:
            status_icon = "🟢"
        elif m.last_status is False:
             status_icon = "🔴"
        else:
            status_icon = "⚪"
            
        markup.add(InlineKeyboardButton(f"{status_icon} {m.name or m.url}", callback_data=f"site_{m.id}"))
    
    markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu"))
    return markup

def site_details_menu(monitor_id, url=None, is_active=True):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    if url:
        buttons.append(InlineKeyboardButton("🌍 Visit Site", url=url))
        
    # Toggle Pause/Resume
    pause_text = "⏸ Pause" if is_active else "▶️ Resume"
    pause_callback = f"pause_{monitor_id}" if is_active else f"resume_{monitor_id}"

    buttons.extend([
        InlineKeyboardButton("🔄 Check Now", callback_data=f"check_{monitor_id}"),
        InlineKeyboardButton(pause_text, callback_data=pause_callback),
        InlineKeyboardButton("📊 Statistics", callback_data=f"stats_{monitor_id}"),
        InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{monitor_id}"),
        InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{monitor_id}"),
        InlineKeyboardButton("🔙 Back to List", callback_data="menu_my_sites")
    ])
    
    markup.add(*buttons)
    return markup

def stats_view_menu(monitor_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back to Site", callback_data=f"site_{monitor_id}"))
    return markup

def monitor_edit_menu(monitor_id, monitor: Monitor):
    markup = InlineKeyboardMarkup(row_width=2)
    
    # Toggle SSL
    ssl_icon = "✅" if monitor.check_ssl else "⬜"
    
    # Keyword Config
    kw_text = "Keywords"
    if monitor.keyword_include or monitor.keyword_exclude:
        kw_text += " (Set)"
        
    markup.add(
        InlineKeyboardButton(f"{ssl_icon} SSL Check", callback_data=f"edit_ssl_{monitor_id}"),
        InlineKeyboardButton(f"📝 {kw_text}", callback_data=f"edit_kw_{monitor_id}")
    )
    
    # Intervals / Latency
    markup.add(
        InlineKeyboardButton(f"⏱ Interval: {monitor.interval_seconds}s", callback_data=f"edit_int_{monitor_id}"),
        InlineKeyboardButton(f"⚡ Latency: {monitor.max_response_time or 'Off'}s", callback_data=f"edit_lat_{monitor_id}")
    )
    
    markup.add(
         InlineKeyboardButton(f"🕙 Timeout: {monitor.timeout_seconds}s", callback_data=f"edit_timeout_{monitor_id}"),
         InlineKeyboardButton(f"🔢 Status: {monitor.expected_status or '2xx'}", callback_data=f"edit_status_{monitor_id}")
    )

    markup.add(InlineKeyboardButton("🔙 Back to Monitor", callback_data=f"site_{monitor_id}"))
    return markup

def cancel_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚫 Cancel", callback_data="cancel_action"))
    return markup

def verification_code_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⬅️ Back", callback_data="back_to_email_setup"),
        InlineKeyboardButton("🚫 Cancel", callback_data="cancel_action")
    )
    return markup

def settings_menu(user_notification_enabled, user_email, email_enabled):
    markup = InlineKeyboardMarkup(row_width=1)
    notif_text = "🔔 Telegram Notifications: ON" if user_notification_enabled else "🔕 Telegram Notifications: OFF"
    markup.add(InlineKeyboardButton(notif_text, callback_data="toggle_global_notif"))
    
    # Email Notifications
    if user_email:
        email_status = "✅ ON" if email_enabled else "❌ OFF"
        email_text = f"📧 Email: {email_status} ({user_email})"
        markup.add(InlineKeyboardButton(email_text, callback_data="config_email"))
    else:
        markup.add(InlineKeyboardButton("📧 Setup Email Alerts", callback_data="setup_email"))
    
    markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu"))
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 System Stats", callback_data="admin_stats"),
        InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton("📧 Manage Quotas", callback_data="admin_quotas"),
        InlineKeyboardButton("🔙 Close", callback_data="admin_close")
    )
    return markup

def admin_broadcast_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Yes, Send", callback_data="broadcast_confirm_yes"),
        InlineKeyboardButton("❌ No, Cancel", callback_data="broadcast_confirm_no")
    )
    return markup
