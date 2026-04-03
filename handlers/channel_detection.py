"""Detect when bot is added/removed from channels/groups."""
import logging
from telegram import Update, ChatMemberUpdated
from telegram.ext import ContextTypes
from database.models import add_managed_channel, remove_managed_channel

logger = logging.getLogger(__name__)

async def channel_detection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle my_chat_member updates."""
    result: ChatMemberUpdated = update.my_chat_member
    if not result:
        return
    old = result.old_chat_member
    new = result.new_chat_member
    chat = result.chat
    user = result.from_user
    old_status = old.status if old else "left"
    new_status = new.status if new else "left"
    if old_status in ("left", "kicked") and new_status in ("administrator", "member"):
        logger.info(f"Bot added to {chat.type} {chat.id} ({chat.title}) by {user.id}")
        await add_managed_channel(chat.id, chat.title or "Untitled", user.id, chat.type)
        try:
            if chat.type in ("group", "supergroup"):
                await context.bot.send_message(chat.id,
                    "\u2705 <b>Telegram Growth Engine activated!</b>\n\nI'll auto-approve join requests and send welcome DMs.",
                    parse_mode="HTML")
        except Exception:
            pass
        try:
            await context.bot.send_message(user.id,
                f"\u2705 I've been added to <b>{chat.title}</b>!\nUse /dashboard to manage settings.",
                parse_mode="HTML")
        except Exception:
            pass
    elif old_status in ("administrator", "member") and new_status in ("left", "kicked"):
        logger.info(f"Bot removed from {chat.id} ({chat.title})")
        await remove_managed_channel(chat.id)
