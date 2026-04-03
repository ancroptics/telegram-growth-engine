"""Keyboard layouts."""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton("\U0001f4ca Dashboard", callback_data="my_channels"),
         InlineKeyboardButton("\U0001f4e2 Broadcast", callback_data="broadcast_menu")],
        [InlineKeyboardButton("\U0001f4cb Templates", callback_data="templates_list"),
         InlineKeyboardButton("\U0001f916 Clone Bot", callback_data="clone_bot")],
        [InlineKeyboardButton("\U0001f310 Cross Promo", callback_data="cross_promo"),
         InlineKeyboardButton("\u23f0 Auto Poster", callback_data="auto_poster")],
        [InlineKeyboardButton("\u2b50 Premium", callback_data="premium_info"),
         InlineKeyboardButton("\U0001f4ac Support", callback_data="support")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("\U0001f527 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)
