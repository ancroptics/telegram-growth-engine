"""Welcome DM editing handlers."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import update_channel_setting, get_managed_channel

logger = logging.getLogger(__name__)


async def handle_welcome_dm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("ch_edit_welcome:"):
        chat_id = int(data.split(":")[1])
        ch = await get_managed_channel(chat_id)
        current = ch.get("welcome_message", "Not set") if ch else "Not set"
        context.user_data["editing_welcome_for"] = chat_id
        text = (f"\ud83d\udcac <b>Edit Welcome DM</b>\n\n"
            f"Current message:\n<i>{current[:500]}</i>\n\n"
            f"Send your new welcome message. Variables:\n"
            f"{{first_name}}, {{last_name}}, {{username}}, {{channel_title}}")
        await query.message.edit_text(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data=f"manage_ch:{chat_id}")]]))


async def welcome_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.pop("editing_welcome_for", None)
    if not chat_id:
        return
    text = update.message.text
    await update_channel_setting(chat_id, welcome_message=text, welcome_dm_enabled=True)
    await update.message.reply_text("\u2705 Welcome message updated!")
