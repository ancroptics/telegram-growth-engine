"""User-facing commands."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from database.models import (
    get_referral_stats, get_owner_channels, get_managed_channel,
    update_channel_setting, get_owner_tier
)
from utils.helpers import format_number
from utils.constants import TIER_EMOJI

logger = logging.getLogger(__name__)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_stats = await get_referral_stats(user.id)
    bot_username = Config.BOT_USERNAME or 'Botofall_robot'
    link = f"https://t.me/{bot_username}?start={user.id}"
    text = (f"👥 <b>Your Referral Link</b>\n\n"
            f"🔗 {link}\n\n"
            f"📊 Referrals: {ref_stats.get('total', 0)}\n"
            f"✅ Active: {ref_stats.get('active', 0)}\n\n"
            f"Share this link to earn rewards!")
    await update.message.reply_text(text, parse_mode="HTML")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channels = await get_owner_channels(user.id)
    tier = await get_owner_tier(user.id)
    ref_stats = await get_referral_stats(user.id)
    total_approved = sum(ch.get("total_approved", 0) for ch in channels)
    total_dms = sum(ch.get("total_dms_sent", 0) for ch in channels)
    total_members = sum(ch.get("member_count", 0) for ch in channels)
    text = (f"📊 <b>Your Stats</b>\n\n"
            f"🏆 Tier: {TIER_EMOJI.get(tier, '')} {tier.capitalize()}\n"
            f"📢 Channels: {len(channels)}\n"
            f"👥 Total Members: {format_number(total_members)}\n"
            f"✅ Total Approved: {format_number(total_approved)}\n"
            f"💬 DMs Sent: {format_number(total_dms)}\n"
            f"👥 Referrals: {ref_stats.get('total', 0)}")
    await update.message.reply_text(text, parse_mode="HTML")

async def setdrip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 4:
        await update.message.reply_text("Usage: /setdrip {channel_id} {rate} {start_hour} {end_hour}")
        return
    try:
        chat_id = int(context.args[0])
        rate = int(context.args[1])
        start_h = int(context.args[2])
        end_h = int(context.args[3])
    except ValueError:
        await update.message.reply_text("All arguments must be numbers.")
        return
    channel = await get_managed_channel(chat_id)
    if not channel:
        await update.message.reply_text("❌ Channel not found.")
        return
    if channel.get("owner_id") != update.effective_user.id:
        await update.message.reply_text("❌ Not your channel.")
        return
    rate = max(1, min(rate, 200))
    start_h = max(0, min(start_h, 23))
    end_h = max(0, min(end_h, 23))
    await update_channel_setting(chat_id, drip_rate=rate, drip_active_start=start_h, drip_active_end=end_h)
    await update.message.reply_text(
        f"✅ Drip settings updated!\n\n"
        f"Rate: {rate} users/5min\n"
        f"Active: {start_h}:00 - {end_h}:00"
    )
