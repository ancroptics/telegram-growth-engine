"""Start command."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import get_or_create_owner, get_or_create_end_user, process_referral
from config import ADMIN_IDS
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
    await get_or_create_owner(user.id, user.username, user.first_name, user.last_name)
    await get_or_create_end_user(user.id, user.username, user.first_name, user.last_name)
    if context.args and context.args[0].startswith("ref_"):
        try:
            rid = int(context.args[0].split("_")[1])
            if rid != user.id: await process_referral(rid, user.id)
        except: pass
    buttons = [
        [InlineKeyboardButton("\U0001f4ca My Channels", callback_data="my_channels"),
         InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="settings")],
        [InlineKeyboardButton("\U0001f4e2 Broadcast", callback_data="broadcast_menu"),
         InlineKeyboardButton("\U0001f4cb Templates", callback_data="templates_menu")],
        [InlineKeyboardButton("\U0001f517 Referral", callback_data="referral_menu"),
         InlineKeyboardButton("\U0001f48e Premium", callback_data="premium_menu")],
        [InlineKeyboardButton("\U0001f4c8 Analytics", callback_data="analytics_menu"),
         InlineKeyboardButton("\u2753 Help", callback_data="help_menu")],
    ]
    if user.id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("\U0001f6e1\ufe0f Admin Panel", callback_data="admin_panel")])
    text = (f"\U0001f44b Welcome, {user.first_name}!\n\n"
            "\U0001f680 *Telegram Growth Engine*\n\n"
            "I help you manage your channels with:\n"
            "\u2022 \u2705 Auto-approve join requests\n"
            "\u2022 \U0001f4e9 Welcome DMs to new members\n"
            "\u2022 \U0001f4e2 Broadcast messages\n"
            "\u2022 \U0001f504 Auto-post to groups\n"
            "\u2022 \U0001f3af Force subscribe\n"
            "\u2022 \U0001f4ca Analytics & insights\n\n"
            "*Add me as admin* to your channel to get started!")
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("\u2753 *Help Guide*\n\n"
            "*Setup:*\n1. Add me as admin to your channel\n"
            "2. Enable Approve New Members in channel settings\n"
            "3. I will auto-approve requests and send welcome DMs\n\n"
            "*Commands:*\n/start - Main menu\n/help - This help\n/stats - View analytics")
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")]]))

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    buttons = [
        [InlineKeyboardButton("\U0001f4ca My Channels", callback_data="my_channels"),
         InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="settings")],
        [InlineKeyboardButton("\U0001f4e2 Broadcast", callback_data="broadcast_menu"),
         InlineKeyboardButton("\U0001f4cb Templates", callback_data="templates_menu")],
        [InlineKeyboardButton("\U0001f517 Referral", callback_data="referral_menu"),
         InlineKeyboardButton("\U0001f48e Premium", callback_data="premium_menu")],
        [InlineKeyboardButton("\U0001f4c8 Analytics", callback_data="analytics_menu"),
         InlineKeyboardButton("\u2753 Help", callback_data="help_menu")],
    ]
    if user.id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("\U0001f6e1\ufe0f Admin Panel", callback_data="admin_panel")])
    try:
        await query.message.edit_text("\U0001f3e0 *Main Menu*\n\nWhat would you like to do?",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    except: pass
