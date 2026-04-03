"""Keyboard layouts."""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton("\ud83d\udcca Dashboard", callback_data="my_channels"),
         InlineKeyboardButton("\ud83d\udce2 Broadcast", callback_data="broadcast_menu")],
        [InlineKeyboardButton("\ud83d\udccb Templates", callback_data="templates_list"),
         InlineKeyboardButton("\ud83e\udd16 Clone Bot", callback_data="clone_bot")],
        [InlineKeyboardButton("\ud83c\udf10 Cross Promo", callback_data="cross_promo"),
         InlineKeyboardButton("\u23f0 Auto Poster", callback_data="auto_poster")],
        [InlineKeyboardButton("\u2b50 Premium", callback_data="premium_info"),
         InlineKeyboardButton("\ud83d\udcac Support", callback_data="support")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("\ud83d\udd27 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)
