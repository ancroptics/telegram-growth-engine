"""Inline keyboard builders."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_kb(is_admin=False):
    kb = [
        [InlineKeyboardButton("\U0001f4e2 My Channels", callback_data="my_channels"),
         InlineKeyboardButton("\U0001f4ca Analytics", callback_data="analytics_overview")],
        [InlineKeyboardButton("\U0001f4e3 Broadcast", callback_data="broadcast_menu"),
         InlineKeyboardButton("\U0001f4dd Templates", callback_data="templates_list")],
        [InlineKeyboardButton("\U0001f916 Auto Poster", callback_data="auto_poster"),
         InlineKeyboardButton("\U0001f916 Bot Clones", callback_data="clone_list")],
        [InlineKeyboardButton("\U0001f465 Referrals", callback_data="user_mgmt"),
         InlineKeyboardButton("\U0001f517 Cross Promo", callback_data="cross_promo")],
        [InlineKeyboardButton("\U0001f48e Premium", callback_data="premium_info"),
         InlineKeyboardButton("\U0001f4ac Support", callback_data="support")],
    ]
    if is_admin:
        kb.append([InlineKeyboardButton("\U0001f512 Superadmin", callback_data="superadmin")])
    return InlineKeyboardMarkup(kb)

def channels_list_kb(channels):
    kb = []
    for ch in channels:
        title = ch.get('chat_title', '?')[:30]
        kb.append([InlineKeyboardButton(f"\U0001f4e2 {title}", callback_data=f"manage_ch:{ch['chat_id']}")])
    kb.append([InlineKeyboardButton("\u2795 Add Channel", callback_data="add_channel")])
    kb.append([InlineKeyboardButton("\u00ab Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(kb)

def channel_manage_kb(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data=f"ch_settings:{chat_id}"),
         InlineKeyboardButton("\U0001f4ca Analytics", callback_data=f"ch_analytics:{chat_id}")],
        [InlineKeyboardButton("\U0001f4cb Pending", callback_data=f"ch_pending:{chat_id}"),
         InlineKeyboardButton("\U0001f4a7 Drip", callback_data=f"drip_config:{chat_id}")],
        [InlineKeyboardButton("\U0001f4dd Welcome DM", callback_data=f"ch_edit_welcome:{chat_id}"),
         InlineKeyboardButton("\U0001f512 Force Sub", callback_data=f"ch_force_sub:{chat_id}")],
        [InlineKeyboardButton("\U0001f310 Language", callback_data=f"ch_i18n:{chat_id}"),
         InlineKeyboardButton("\U0001f517 Cross Promo", callback_data=f"ch_cross_promo:{chat_id}")],
        [InlineKeyboardButton("\U0001f4e4 Export CSV", callback_data=f"ch_export:{chat_id}")],
        [InlineKeyboardButton("\U0001f5d1 Remove Channel", callback_data=f"ch_delete:{chat_id}")],
        [InlineKeyboardButton("\u00ab Back", callback_data="my_channels")],
    ])

def channel_settings_kb(chat_id, channel):
    def toggle_icon(val): return '\u2705' if val else '\u274c'
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{toggle_icon(channel.get('auto_approve'))} Auto-Approve", callback_data=f"ch_toggle:{chat_id}:auto_approve")],
        [InlineKeyboardButton(f"{toggle_icon(channel.get('welcome_dm_enabled'))} Welcome DM", callback_data=f"ch_toggle:{chat_id}:welcome_dm_enabled")],
        [InlineKeyboardButton(f"{toggle_icon(channel.get('drip_enabled'))} Drip Approve", callback_data=f"ch_toggle:{chat_id}:drip_enabled")],
        [InlineKeyboardButton(f"{toggle_icon(channel.get('force_subscribe_enabled'))} Force Subscribe", callback_data=f"ch_toggle:{chat_id}:force_subscribe_enabled")],
        [InlineKeyboardButton("\u00ab Back", callback_data=f"manage_ch:{chat_id}")],
    ])

def batch_kb(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\u2705 Approve All", callback_data=f"batch_approve:{chat_id}"),
         InlineKeyboardButton("\u274c Decline All", callback_data=f"batch_decline:{chat_id}")],
        [InlineKeyboardButton("\U0001f4a7 Start Drip", callback_data=f"drip_start:{chat_id}")],
        [InlineKeyboardButton("\u00ab Back", callback_data=f"manage_ch:{chat_id}")],
    ])

def drip_kb(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\u25b6\ufe0f Start Drip", callback_data=f"drip_start:{chat_id}")],
        [InlineKeyboardButton("\u00ab Back", callback_data=f"manage_ch:{chat_id}")],
    ])

def force_subscribe_kb(chat_id, enabled):
    toggle_text = '\u23f8 Disable' if enabled else '\u25b6\ufe0f Enable'
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_text, callback_data=f"fs_toggle:{chat_id}")],
        [InlineKeyboardButton("\u2795 Add Channel", callback_data=f"fs_add:{chat_id}")],
        [InlineKeyboardButton("\u00ab Back", callback_data=f"manage_ch:{chat_id}")],
    ])

def broadcast_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\u00ab Back", callback_data="main_menu")],
    ])

def clone_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\u2795 Add Clone", callback_data="clone_add")],
        [InlineKeyboardButton("\u00ab Back", callback_data="main_menu")],
    ])

def admin_panel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f465 Users", callback_data="sa_users"),
         InlineKeyboardButton("\U0001f4e3 Global Broadcast", callback_data="sa_broadcast")],
        [InlineKeyboardButton("\u00ab Back", callback_data="main_menu")],
    ])

def premium_upgrade_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f48e Buy Premium", callback_data="premium_buy:premium")],
        [InlineKeyboardButton("\U0001f4bc Buy Business", callback_data="premium_buy:business")],
        [InlineKeyboardButton("\u00ab Back", callback_data="main_menu")],
    ])

def category_kb(chat_id, categories=None):
    from utils.constants import CATEGORIES
    cats = categories or CATEGORIES
    kb = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(cat, callback_data=f"cp_cat:{chat_id}:{cat}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("\u00ab Back", callback_data=f"manage_ch:{chat_id}")])
    return InlineKeyboardMarkup(kb)

def back_kb(target="main_menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data=target)]])
