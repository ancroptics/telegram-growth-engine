"""Start command and main menu."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import Config

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        from database.models import ensure_user, get_owner_channels, get_referral_stats, get_owner_tier
        from utils.helpers import format_number
        from utils.constants import TIER_EMOJI
        from utils.keyboards import main_menu_kb
        referrer_id = None
        if context.args:
            try:
                referrer_id = int(context.args[0])
                if referrer_id == user.id: referrer_id = None
            except ValueError: pass
        await ensure_user(user.id, user.username, user.full_name, referrer_id)
        channels = await get_owner_channels(user.id)
        tier = await get_owner_tier(user.id)
        ref_stats = await get_referral_stats(user.id)
        total_approved = sum(ch.get("total_approved", 0) for ch in channels)
        text = (f"\U0001f680 <b>TELEGRAM GROWTH ENGINE v3.0</b>\n\n"
                f"Welcome, {user.first_name}!\n\n"
                f"\U0001f4e2 Channels: {len(channels)}\n"
                f"\u2705 Total Approved: {format_number(total_approved)}\n"
                f"\U0001f465 Referrals: {ref_stats.get('total', 0)}\n"
                f"\U0001f3c6 Tier: {TIER_EMOJI.get(tier, '')} {tier.capitalize()}\n\n"
                f"\u2b07\ufe0f <b>Quick Start:</b> Add this bot as admin to your channel.")
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_kb(is_admin=user.id in Config.SUPERADMIN_IDS))
    except Exception as e:
        logger.error(f"Start command error: {e}")
        text = (f"\U0001f680 <b>TELEGRAM GROWTH ENGINE v3.0</b>\n\n"
                f"Welcome, {user.first_name}!\n\n"
                f"\u26a0\ufe0f Database is currently unavailable. "
                f"Some features may not work.\n\n"
                f"Please try again later or contact support.")
        await update.message.reply_text(text, parse_mode="HTML")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()
    try:
        from database.models import get_owner_channels, get_referral_stats, get_owner_tier
        from utils.helpers import format_number
        from utils.constants import TIER_EMOJI
        from utils.keyboards import main_menu_kb
        channels = await get_owner_channels(user.id)
        tier = await get_owner_tier(user.id)
        ref_stats = await get_referral_stats(user.id)
        total_approved = sum(ch.get("total_approved", 0) for ch in channels)
        text = (f"\U0001f680 <b>TELEGRAM GROWTH ENGINE v3.0</b>\n\n"
                f"\U0001f4e2 Channels: {len(channels)}\n"
                f"\u2705 Total Approved: {format_number(total_approved)}\n"
                f"\U0001f465 Referrals: {ref_stats.get('total', 0)}\n"
                f"\U0001f3c6 Tier: {TIER_EMOJI.get(tier, '')} {tier.capitalize()}")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb(is_admin=user.id in Config.SUPERADMIN_IDS))
    except Exception as e:
        logger.error(f"Main menu error: {e}")
        await query.message.edit_text("\u26a0\ufe0f Database unavailable. Try again later.", parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("\U0001f4d6 <b>HELP</b>\n\n"
            "<b>Setup:</b>\n"
            "1. Add bot as admin to your channel\n"
            "2. Enable 'Approve New Members' in channel settings\n"
            "3. The bot handles the rest!\n\n"
            "<b>Commands:</b>\n"
            "/start - Main menu\n"
            "/dashboard - Channel dashboard\n"
            "/referral - Your referral link\n"
            "/stats - Your stats\n"
            "/premium - Upgrade info\n"
            "/help - This message\n\n"
            "<b>Channel Owner:</b>\n"
            "/broadcast - Send to all users\n"
            "/newtemplate - Create DM template\n"
            "/autopost - Set up auto-poster\n"
            "/setdrip <id> <rate> <start> <end>")
    await update.message.reply_text(text, parse_mode="HTML")

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers.channel_settings import show_channels_list
        await show_channels_list(update, context, is_command=True)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        await update.message.reply_text("\u26a0\ufe0f Database unavailable. Try again later.")
