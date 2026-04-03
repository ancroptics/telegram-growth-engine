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
    text = (f"Welcome, {first_name}!\n\nI'm the Telegram Growth Engine.\n\nGet started: Add me as an admin to your channel!")
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_kb(is_admin))
