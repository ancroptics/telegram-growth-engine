"""Multi-language welcome message management."""
import json, logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_managed_channel, update_channel_setting
from utils.keyboards import back_kb

logger = logging.getLogger(__name__)
SUPPORTED_LANGS = {"en":"English","hi":"Hindi","es":"Spanish","fr":"French","ar":"Arabic","ru":"Russian","pt":"Portuguese","de":"German","zh":"Chinese","ja":"Japanese","ko":"Korean","tr":"Turkish"}

async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    if data.startswith("ch_i18n:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        i18n = channel.get("welcome_messages_i18n") or {}
        if isinstance(i18n, str): i18n = json.loads(i18n)
        text = "🌐 <b>Multi-Language Welcome</b>\n\n"
        for code, name in SUPPORTED_LANGS.items():
            has = "✅" if code in i18n else "❌"
            text += f"{has} {name}\n"
        text += f"\nUse /setlang {chat_id} <lang_code> to set."
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb(f"manage_ch:{chat_id}"))
