"""Start and dashboard command handlers."""
import logging
from html import escape as html_escape
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import ensure_user, get_owner_channels
from utils.keyboards import main_menu_kb
from config import Config

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    await ensure_user(user.id, user.username, user.full_name)

    # Check for deep link
    args = context.args
    if args and args[0].startswith("fsub_"):
        chat_id = int(args[0].replace("fsub_", ""))
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("\u2705 Verify Membership", callback_data=f"fs_verify:{chat_id}")]
        ])
        await update.message.reply_text(
            "\ud83d\udc4b Click below to verify your membership and get approved:",
            reply_markup=kb
        )
        return

    is_admin = user.id in Config.SUPERADMIN_IDS
    text = (
        f"\ud83d\udc4b <b>Welcome, {html_escape(user.first_name)}!</b>\n\n"
        f"I'm the <b>Telegram Growth Engine</b> bot. I help you:\n\n"
        f"\ud83d\udce2 Auto-approve join requests\n"
        f"\ud83d\udcac Send welcome DMs\n"
        f"\ud83d\udd12 Force subscribe to other channels\n"
        f"\ud83d\udca7 Drip approve for natural growth\n"
        f"\ud83d\udcca Track analytics & stats\n"
        f"\ud83c\udf10 Multi-language welcome messages\n\n"
        f"<b>Getting started:</b>\n"
        f"1\ufe0f\u20e3 Add me as admin to your channel\n"
        f"2\ufe0f\u20e3 Enable 'Approve New Members' in channel settings\n"
        f"3\ufe0f\u20e3 Use /dashboard to manage everything\n"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_kb(is_admin))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "\u2753 <b>Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start \u2014 Main menu\n"
        "/dashboard \u2014 Your channels\n"
        "/referral \u2014 Referral stats\n"
        "/stats \u2014 Your stats\n"
        "/help \u2014 This message\n\n"
        "<b>How it works:</b>\n"
        "1. Add me as admin to your channel\n"
        "2. Enable 'Approve New Members' in channel settings\n"
        "3. I auto-approve and send welcome DMs\n\n"
        "Questions? Use /start \u2192 \ud83d\udcac Support"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard \u2014 show user's channels."""
    user = update.effective_user
    channels = await get_owner_channels(user.id)

    if not channels:
        text = (
            "\ud83d\udcca <b>Dashboard</b>\n\n"
            "You don't have any channels connected yet!\n\n"
            "<b>To get started:</b>\n"
            "1. Add me as an admin to your channel\n"
            "2. Give me 'Invite Users via Link' permission\n"
            "3. I'll appear here automatically!"
        )
        await update.message.reply_text(text, parse_mode="HTML")
        return

    text = f"\ud83d\udcca <b>Dashboard</b>\n\nYou manage <b>{len(channels)}</b> channel(s):\n\n"
    buttons = []
    for ch in channels:
        title = html_escape(ch.get("chat_title", "Unknown"))
        members = ch.get("member_count", 0)
        approved = ch.get("total_approved", 0)
        text += f"\ud83d\udce2 <b>{title}</b> \u2014 \ud83d\udc65 {members} | \u2705 {approved}\n"
        buttons.append([InlineKeyboardButton(f"\u2699\ufe0f {title[:30]}", callback_data=f"manage_ch:{ch['chat_id']}")])
    buttons.append([InlineKeyboardButton("\u00ab Back to Menu", callback_data="main_menu")])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu from callback query."""
    query = update.callback_query
    user = update.effective_user
    is_admin = user.id in Config.SUPERADMIN_IDS
    text = (
        f"\ud83d\udc4b <b>Main Menu</b>\n\n"
        f"What would you like to do?"
    )
    await query.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb(is_admin))


async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support info."""
    query = update.callback_query
    await query.message.edit_text(
        "\ud83d\udcac <b>Support</b>\n\n"
        "Need help? Contact the bot admin.\n\n"
        "Common issues:\n"
        "\u2022 Make sure bot is admin in your channel\n"
        "\u2022 Enable 'Approve New Members' in channel settings\n"
        "\u2022 Give bot permission to invite users",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="main_menu")]])
    )
