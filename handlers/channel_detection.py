"""Detect when bot is added/removed from channels."""
import logging
from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from database.models import add_managed_channel, remove_managed_channel, get_channel_owner, register_channel_owner
from config import Config

logger = logging.getLogger(__name__)

async def channel_detection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_member = update.my_chat_member
    if not my_member: return
    chat = my_member.chat
    old = my_member.old_chat_member
    new = my_member.new_chat_member
    user = my_member.from_user
    if not user: return
    
    old_status = old.status if old else "left"
    new_status = new.status if new else "left"
    
    # Bot added as admin
    if old_status in ("left", "kicked") and new_status in ("administrator", "member"):
        if chat.type in ("channel", "supergroup"):
            logger.info(f"Bot added to {chat.type} '{chat.title}' by {user.id}")
            owner = await get_channel_owner(user.id)
            if not owner:
                await register_channel_owner(user.id, user.username, user.full_name)
            try:
                member_count = await context.bot.get_chat_member_count(chat.id)
            except Exception:
                member_count = 0
            await add_managed_channel(
                chat_id=chat.id, chat_title=chat.title, chat_type=chat.type,
                chat_username=chat.username, owner_id=user.id, member_count=member_count
            )
            try:
                await context.bot.send_message(
                    user.id,
                    f"\u2705 <b>Channel Connected!</b>\n\n"
                    f"\ud83d\udce2 {chat.title}\n"
                    f"\ud83d\udc65 Members: {member_count}\n\n"
                    f"The bot will now auto-approve join requests and send welcome DMs.\n"
                    f"Use /dashboard to configure.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify owner {user.id}: {e}")
    
    # Bot removed
    elif old_status in ("administrator", "member") and new_status in ("left", "kicked"):
        if chat.type in ("channel", "supergroup"):
            logger.info(f"Bot removed from '{chat.title}' by {user.id}")
            await remove_managed_channel(chat.id)
            try:
                await context.bot.send_message(user.id, f"\u274c Bot removed from {chat.title}.")
            except Exception:
                pass
