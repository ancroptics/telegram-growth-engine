"""Welcome DM editing."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_managed_channel, update_channel_setting
from utils.keyboards import back_kb
from utils.constants import WELCOME_VARIABLES

logger = logging.getLogger(__name__)

async def handle_welcome_dm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    if data.startswith("ch_edit_welcome:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        current = channel.get("welcome_message", "Not set")
        vars_text = "\n".join(f"  {k} — {v}" for k, v in WELCOME_VARIABLES.items())
        text = (f"📝 <b>Edit Welcome DM</b>\n\n"
                f"Current message:\n<code>{current[:500]}</code>\n\n"
                f"Variables:\n{vars_text}\n\n"
                f"Send your new welcome message now. /cancel to abort")
        context.user_data["editing_welcome_for"] = chat_id
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb(f"manage_ch:{chat_id}"))

async def welcome_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get("editing_welcome_for")
    if not chat_id: return False
    message = update.message
    if message.text and message.text.startswith("/cancel"):
        del context.user_data["editing_welcome_for"]
        await message.reply_text("❌ Cancelled.")
        return True
    if message.photo:
        await update_channel_setting(chat_id, welcome_message=message.caption or "", welcome_media_type="photo", welcome_media_file_id=message.photo[-1].file_id)
    elif message.video:
        await update_channel_setting(chat_id, welcome_message=message.caption or "", welcome_media_type="video", welcome_media_file_id=message.video.file_id)
    elif message.text:
        await update_channel_setting(chat_id, welcome_message=message.text, welcome_media_type=None, welcome_media_file_id=None)
    else:
        await message.reply_text("Unsupported. Send text, photo, or video.")
        return True
    del context.user_data["editing_welcome_for"]
    await message.reply_text("✅ Welcome message updated!")
    return True
