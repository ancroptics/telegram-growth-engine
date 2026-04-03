"""Stub handler for user_mgmt."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_user_mgmt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(
        "🚧 This feature is coming soon!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="main_menu")]])
    )
