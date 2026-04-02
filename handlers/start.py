"""Start command and main menu."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import ensure_user, get_owner_channels, get_referral_stats, get_owner_tier
from utils.keyboards import main_menu_kb
from utils.helpers import format_number
from utils.constants import TIER_EMOJI
from config import Config

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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
    text = (f"\ud83d\ude80 <b>TELEGRAM GROWTH ENGINE v3.0</b>\n\n"
            f"Welcome, {user.first_name}!\n\n"
            f"\ud83d\udce2 Channels: {len(channels)}\n"
            f"\u2705 Total Approved: {format_number(total_approved)}\n"
            f"\ud83d\udc65 Referrals: {ref_stats.get('total', 0)}\n"
            f"\ud83c\udfc6 Tier: {TIER_EMOJI.get(tier, '')} {tier.capitalize()}\n\n"
            f"\u2b07\ufe0f <b>Quick Start:</b> Add this bot as admin to your channel.")
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_kb(is_admin=user.id in Config.SUPERADMIN_IDS))

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()
    channels = await get_owner_channels(user.id)
    tier = await get_owner_tier(user.id)
    ref_stats = await get_referral_stats(user.id)
    total_approved = sum(ch.get("total_approved", 0) for ch in channels)
    text = (f"\ud83d\ude80 <b>TELEGRAM GROWTH ENGINE v3.0</b>\n\n"
            f"\ud83d\udce2 Channels: {len(channels)}\n"
            f"\u2705 Total Approved: {format_number(total_approved)}\n"
            f"\ud83d\udc65 Referrals: {ref_stats.get('total', 0)}\n"
            f"\ud83c\udfc6 Tier: {TIER_EMOJI.get(tier, '')} {tier.capitalize()}")
    await query.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb(is_admin=user.id in Config.SUPERADMIN_IDS))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("\ud83d\udcd6 <b>HELP</b>\n\n"
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
    from handlers.channel_settings import show_channels_list
    await show_channels_list(update, context, is_command=True)
