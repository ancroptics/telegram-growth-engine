"""Start, help, and dashboard command handlers."""
import logging
from html import escape as html_escape
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import Config
from database.models import get_or_create_owner, get_or_create_end_user, get_owner_channels
from utils.keyboards import main_menu_kb

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    if not user:
        return

    # Check for referral
    referred_by = None
    if context.args and context.args[0].startswith("ref_"):
        try:
            referred_by = int(context.args[0][4:])
        except (ValueError, IndexError):
            pass

    # Register/get owner
    owner = await get_or_create_owner(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    # Also register as end user (for broadcasts etc)
    await get_or_create_end_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        referred_by=referred_by,
    )

    if owner and owner.get("is_banned"):
        await update.message.reply_text("\u26d4 Your account has been suspended.")
        return

    is_admin = user.id in Config.ADMIN_IDS or user.id in Config.SUPERADMIN_IDS
    first_name = html_escape(user.first_name or "there")

    text = (
        f"\ud83c\udf1f <b>Welcome, {first_name}!</b>\n\n"
        f"I'm the <b>Telegram Growth Engine</b> \u2014 your all-in-one tool for:\n\n"
        f"\u2705 Auto-approving join requests\n"
        f"\ud83d\udcac Sending welcome DMs\n"
        f"\ud83d\udce2 Broadcasting to your audience\n"
        f"\ud83d\udd12 Force subscribe gates\n"
        f"\u23f0 Auto-posting to groups\n"
        f"\ud83d\udcca Analytics & insights\n\n"
        f"<b>Get started:</b> Add me as an admin to your channel!"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu_kb(is_admin),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    text = (
        "\ud83d\udcda <b>Commands</b>\n\n"
        "/start \u2014 Main menu\n"
        "/dashboard \u2014 Channel dashboard\n"
        "/stats \u2014 Your stats\n"
        "/referral \u2014 Referral link & stats\n"
        "/setdrip <channel_id> <rate> \u2014 Set drip rate\n"
        "/newtemplate <name> \u2014 Create a template\n"
        "/deltemplate <name> \u2014 Delete a template\n"
        "/autopost \u2014 Auto poster settings\n"
        "/help \u2014 This message\n\n"
        "<b>How to start:</b>\n"
        "1. Add me to your channel as admin\n"
        "2. Enable \"Approve New Members\" in channel settings\n"
        "3. I'll auto-approve requests and send welcome DMs!\n\n"
        "\ud83d\udcac Support: @TGESupport"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command."""
    user = update.effective_user
    channels = await get_owner_channels(user.id)

    if not channels:
        await update.message.reply_text(
            "\ud83d\udcca <b>Dashboard</b>\n\n"
            "No channels connected yet!\n"
            "Add me as admin to a channel to get started.",
            parse_mode="HTML",
        )
        return

    text = "\ud83d\udcca <b>Your Channels</b>\n\n"
    buttons = []
    for ch in channels:
        title = html_escape(ch.get("chat_title", "Unknown"))[:30]
        status = "\ud83d\udfe2" if ch.get("auto_approve") else "\ud83d\udd34"
        text += f"{status} <b>{title}</b>\n"
        buttons.append([InlineKeyboardButton(f"\ud83d\udce2 {title}", callback_data=f"manage_ch:{ch['chat_id']}")])

    buttons.append([InlineKeyboardButton("\u00ab Main Menu", callback_data="main_menu")])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
