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
    user = update.effective_user
    if not user:
        return
    referred_by = None
    if context.args and context.args[0].startswith("ref_"):
        try:
            referred_by = int(context.args[0][4:])
        except (ValueError, IndexError):
            pass
    owner = await get_or_create_owner(user_id=user.id, username=user.username, first_name=user.first_name)
    await get_or_create_end_user(user_id=user.id, username=user.username, first_name=user.first_name, referred_by=referred_by)
    if owner and owner.get("is_banned"):
        await update.message.reply_text("Your account has been suspended.")
        return
    is_admin = user.id in Config.ADMIN_IDS or user.id in Config.SUPERADMIN_IDS
    first_name = html_escape(user.first_name or "there")
    text = (
        f"\U0001f31f <b>Welcome, {first_name}!</b>\n\n"
        f"I'm the <b>Telegram Growth Engine</b> \u2014 your all-in-one tool for:\n\n"
        f"\u2705 Auto-approving join requests\n"
        f"\U0001f4ac Sending welcome DMs\n"
        f"\U0001f4e2 Broadcasting to your audience\n"
        f"\U0001f512 Force subscribe gates\n"
        f"\u23f0 Auto-posting to groups\n"
        f"\U0001f4ca Analytics & insights\n\n"
        f"<b>Get started:</b> Add me as an admin to your channel!"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_kb(is_admin))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "\U0001f4da <b>Commands</b>\n\n"
        "/start \u2014 Main menu\n"
        "/dashboard \u2014 Channel dashboard\n"
        "/stats \u2014 Your stats\n"
        "/referral \u2014 Referral link & stats\n"
        "/setdrip <channel_id> <rate> \u2014 Set drip rate\n"
        "/help \u2014 This message\n\n"
        "<b>How to start:</b>\n"
        "1. Add me to your channel as admin\n"
        "2. Enable \"Approve New Members\" in channel settings\n"
        "3. I'll auto-approve requests and send welcome DMs!\n\n"
        "\U0001f4ac Support: @TGESupport"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    channels = await get_owner_channels(user.id)
    if not channels:
        await update.message.reply_text(
            "\U0001f4ca <b>Dashboard</b>\n\nNo channels connected yet!\nAdd me as admin to a channel to get started.",
            parse_mode="HTML",
        )
        return
    text = "\U0001f4ca <b>Your Channels</b>\n\n"
    buttons = []
    for ch in channels:
        title = html_escape(ch.get("chat_title", "Unknown"))[:30]
        status = "\U0001f7e2" if ch.get("auto_approve") else "\U0001f534"
        text += f"{status} <b>{title}</b>\n"
        buttons.append([InlineKeyboardButton(f"\U0001f4e2 {title}", callback_data=f"manage_ch:{ch['chat_id']}")] )
    buttons.append([InlineKeyboardButton("\u00ab Main Menu", callback_data="main_menu")])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
