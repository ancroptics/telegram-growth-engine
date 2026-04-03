from html import escape as html_escape
"""Cross-promotion management."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import get_owner_channels, get_managed_channel, upsert_cross_promo
from utils.keyboards import category_kb, back_kb

logger = logging.getLogger(__name__)

async def handle_cross_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user
    await query.answer()

    if data == "cross_promo":
        channels = await get_owner_channels(user.id)
        text = "🔗 <b>Cross-Promotion</b>\n\n"
        if not channels:
            text += "Add a channel first!"
        else:
            for ch in channels:
                cp = "✅" if ch.get("cross_promo_enabled") else "❌"
                text += f"📢 {html_escape(ch.get('chat_title','?'))}: {cp}\n"
            text += "\nSelect a channel to configure:"
        kb = []
        for ch in channels:
            kb.append([InlineKeyboardButton(f"📢 {ch.get('chat_title','?')[:25]}", callback_data=f"ch_cross_promo:{ch['chat_id']}")])  
        kb.append([InlineKeyboardButton("« Back", callback_data="main_menu")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("ch_cross_promo:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        enabled = channel.get('cross_promo_enabled', False)
        text = (f"🔗 <b>Cross Promo: {html_escape(channel.get('chat_title',''))}</b>\n\n"
                f"Status: {'✅ Enabled' if enabled else '❌ Disabled'}\n"
                f"Category: {channel.get('cross_promo_category', 'Not set')}\n\n"
                f"Select a category to enable:")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=category_kb(chat_id))

    elif data.startswith("cp_cat:"):
        parts = data.split(":")
        chat_id = int(parts[1])
        category = parts[2]
        await upsert_cross_promo(chat_id, user.id, category)
        await query.message.edit_text(f"✅ Cross-promo enabled for category: {category}", parse_mode="HTML", reply_markup=back_kb(f"ch_cross_promo:{chat_id}"))
