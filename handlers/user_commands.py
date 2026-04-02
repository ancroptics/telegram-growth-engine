"""User-facing commands."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_referral_stats, get_owner_channels, get_owner_tier, ensure_user
from utils.helpers import format_number
from utils.constants import TIER_EMOJI, TIER_LIMITS
from config import Config

logger = logging.getLogger(__name__)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user(user.id, user.username, user.full_name)
    ref_stats = await get_referral_stats(user.id)
    link = f"https://t.me/{Config.BOT_USERNAME}?start={user.id}"
    text = (f"\ud83d\udc65 <b>REFERRAL PROGRAM</b>\n\n"
            f"Your link:\n<code>{link}</code>\n\n"
            f"\ud83d\udcca Stats:\n"
            f"  \u2022 Total referrals: {ref_stats.get('total', 0)}\n"
            f"  \u2022 Active (with channels): {ref_stats.get('active', 0)}\n\n"
            f"\ud83c\udfc6 Rewards:\n"
            f"  5 referrals \u2192 +1 channel slot\n"
            f"  15 referrals \u2192 Premium 7 days\n"
            f"  50 referrals \u2192 Business 30 days")
    await update.message.reply_text(text, parse_mode="HTML")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channels = await get_owner_channels(user.id)
    tier = await get_owner_tier(user.id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    total_approved = sum(ch.get("total_approved", 0) for ch in channels)
    total_dms = sum(ch.get("total_dms_sent", 0) for ch in channels)
    total_members = sum(ch.get("member_count", 0) for ch in channels)
    text = (f"\ud83d\udcca <b>YOUR STATS</b>\n\n"
            f"\ud83c\udfc6 Tier: {TIER_EMOJI.get(tier,'')} {tier.capitalize()}\n"
            f"\ud83d\udce2 Channels: {len(channels)}/{limits['max_channels']}\n"
            f"\ud83d\udc65 Total Members: {format_number(total_members)}\n"
            f"\u2705 Total Approved: {format_number(total_approved)}\n"
            f"\ud83d\udcac DMs Sent: {format_number(total_dms)}\n\n")
    if channels:
        text += "<b>Channels:</b>\n"
        for ch in channels:
            text += (f"  \ud83d\udce2 {ch.get('chat_title','?')[:25]}\n"
                     f"    Members: {format_number(ch.get('member_count',0))} | "
                     f"Approved: {format_number(ch.get('total_approved',0))}\n")
    await update.message.reply_text(text, parse_mode="HTML")

async def setdrip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.models import update_channel_setting, get_managed_channel
    args = context.args
    if not args or len(args) < 4:
        await update.message.reply_text("Usage: /setdrip <channel_id> <rate> <start_hour> <end_hour>")
        return
    try:
        chat_id = int(args[0])
        rate = min(int(args[1]), 500)
        start_h = max(0, min(int(args[2]), 23))
        end_h = max(1, min(int(args[3]), 24))
        channel = await get_managed_channel(chat_id)
        if not channel or channel.get("owner_id") != update.effective_user.id:
            await update.message.reply_text("\u274c Not your channel.")
            return
        await update_channel_setting(chat_id, drip_rate=rate, drip_active_start=start_h, drip_active_end=end_h)
        await update.message.reply_text(f"\u2705 Drip config updated: {rate}/5min, active {start_h}:00-{end_h}:00")
    except ValueError:
        await update.message.reply_text("Invalid values.")
