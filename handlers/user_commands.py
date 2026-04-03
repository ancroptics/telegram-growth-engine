"""User commands: /referral, /stats, /setdrip."""
import logging
from html import escape as html_escape
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_referral_stats, get_owner_channels, get_channel_stats, update_channel_setting
from config import Config

logger = logging.getLogger(__name__)


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = await get_referral_stats(user.id)
    bot_username = Config.BOT_USERNAME
    link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    await update.message.reply_text(
        f"\ud83d\udd17 <b>Your Referral Stats</b>\n\n"
        f"Total referred: <b>{stats.get('total', 0)}</b>\n"
        f"Active: <b>{stats.get('active', 0)}</b>\n\n"
        f"Your referral link:\n<code>{link}</code>",
        parse_mode="HTML")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channels = await get_owner_channels(user.id)
    if not channels:
        await update.message.reply_text("\ud83d\udcca No channels connected yet. Add me as admin to a channel!")
        return
    text = "\ud83d\udcca <b>Your Stats (last 7 days)</b>\n\n"
    for ch in channels:
        title = html_escape(ch.get("chat_title", "Unknown"))
        stats = await get_channel_stats(ch["chat_id"], 7)
        total_approved = sum(s.get("requests_approved", 0) for s in stats)
        total_dms = sum(s.get("dms_sent", 0) for s in stats)
        text += f"\ud83d\udce2 <b>{title}</b>\n  \u2705 {total_approved} approved | \ud83d\udcac {total_dms} DMs\n\n"
    await update.message.reply_text(text, parse_mode="HTML")


async def setdrip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /setdrip <channel_id> <rate>\nExample: /setdrip -1001234567890 5")
        return
    try:
        chat_id = int(args[0])
        rate = int(args[1])
    except ValueError:
        await update.message.reply_text("\u274c Invalid arguments. Use numbers.")
        return
    await update_channel_setting(chat_id, drip_enabled=True, drip_rate=rate)
    await update.message.reply_text(f"\u2705 Drip rate set to {rate} for channel {chat_id}")
