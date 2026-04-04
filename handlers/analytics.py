"""Analytics handler."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import get_owner_channels, get_channel_daily_stats, get_global_stats
from config import ADMIN_IDS
logger = logging.getLogger(__name__)

async def analytics_menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    channels = await get_owner_channels(query.from_user.id)
    buttons = [[InlineKeyboardButton(ch.get("chat_title","?"), callback_data=f"ch_analytics:{ch['chat_id']}")] for ch in channels]
    buttons.append([InlineKeyboardButton("Back", callback_data="main_menu")])
    await query.message.edit_text("Select channel for analytics:", reply_markup=InlineKeyboardMarkup(buttons))

async def channel_analytics_callback(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[1])
    stats = await get_channel_daily_stats(chat_id, days=7)
    if not stats:
        text = "No data yet for this channel."
    else:
        text = "Last 7 days:\n\n"
        for s in stats:
            text += f"{s.get('date','?')}: +{s.get('joins',0)} joins, {s.get('approvals',0)} approved, {s.get('dms_sent',0)} DMs\n"
    await query.message.edit_text(text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="analytics_menu")]]))

async def stats_command(update, context):
    user = update.effective_user
    if user.id in ADMIN_IDS:
        gs = await get_global_stats()
        text = (f"Global Stats\n\nOwners: {gs['total_owners']}\nChannels: {gs['total_channels']}\n"
                f"Users: {gs['total_users']}\nPremium: {gs['premium_owners']}\nClones: {gs['total_clones']}")
    else:
        channels = await get_owner_channels(user.id)
        text = f"Your channels: {len(channels)}\n"
        for ch in channels:
            text += f"\n{ch.get('chat_title','?')}: {ch.get('total_approved',0)} approved, {ch.get('total_dm_sent',0)} DMs"
    await update.message.reply_text(text)
