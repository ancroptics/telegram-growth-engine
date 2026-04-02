"""Cross-promotion management."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_owner_channels, update_channel_setting
from utils.keyboards import category_kb, back_kb

logger = logging.getLogger(__name__)

async def handle_cross_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user
    await query.answer()
    channels = await get_owner_channels(user.id)
    text = "🔄 <b>Cross-Promotion</b>\n\n"
    for ch in channels:
        cp = "✅" if ch.get("cross_promo_enabled") else "❌"
        text += f"📢 {ch.get('chat_title','?')}: {cp}\n"
    text += "\nUse /crosspromo <channel_id> to enable."
    await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb())
