"""Handle chat join requests — auto-approve, force sub check, welcome DM."""
import json
import logging
from telegram import Update, ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import (
    get_managed_channel, record_join_request, approve_join_request_db,
    get_force_sub_channels, update_channel_stats, increment_dm_count
)
from services.language_service import get_welcome_for_language
from services.watermark_service import get_watermark
from utils.helpers import replace_variables

logger = logging.getLogger(__name__)


async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ChatJoinRequest events."""
    req: ChatJoinRequest = update.chat_join_request
    if not req:
        return

    chat = req.chat
    user = req.from_user
    logger.info(f"Join request: user={user.id} chat={chat.id} ({chat.title})")

    channel = await get_managed_channel(chat.id)
    if not channel:
        logger.debug(f"Chat {chat.id} not managed, ignoring join request")
        return

    # Save join request as PENDING
    await record_join_request(
        chat_id=chat.id,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    # Check auto_approve
    auto_approve = channel.get("auto_approve", True)
    if not auto_approve:
        logger.info(f"Auto-approve disabled for {chat.id}, saved as pending")
        return

    # Check drip mode
    drip_enabled = channel.get("drip_enabled", False)
    if drip_enabled:
        logger.info(f"Drip mode for {chat.id}, saved as pending for drip processing")
        return

    # Check force subscribe
    force_channels = await get_force_sub_channels(chat.id)
    if force_channels:
        not_joined = []
        for fc in force_channels:
            try:
                fc_id = fc.get("required_chat_id")
                if not fc_id:
                    continue
                member = await context.bot.get_chat_member(fc_id, user.id)
                if member.status in ("left", "kicked", "banned"):
                    not_joined.append(fc)
            except Exception as e:
                logger.warning(f"Force sub check error: {e}")
                pass

        if not_joined:
            try:
                buttons = []
                for fc in not_joined:
                    title = fc.get("required_chat_title", "Channel")
                    buttons.append([InlineKeyboardButton(f"\ud83d\udce2 Join {title}", url=f"https://t.me/{fc.get('required_chat_id', '')}" )])
                buttons.append([InlineKeyboardButton("\u2705 I've Joined \u2014 Verify", callback_data=f"fs_verify:{chat.id}")])
                
                await context.bot.send_message(
                    user.id,
                    f"\ud83d\udc4b To join <b>{chat.title}</b>, please join these channels first:\n\n"
                    + "\n".join([f"  \u2192 {fc.get('required_chat_title', '?')}" for fc in not_joined])
                    + "\n\nAfter joining, tap the button below:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                logger.info(f"Sent force sub DM to {user.id} for {chat.id}")
            except Exception as e:
                logger.error(f"Failed to send force sub DM to {user.id}: {e}")
                await _approve_and_welcome(context, chat, user, channel)
            return

    # All clear \u2014 approve and welcome
    await _approve_and_welcome(context, chat, user, channel)


async def _approve_and_welcome(context, chat, user, channel):
    """Send welcome DM first, then approve the join request."""
    dm_sent = False
    if channel.get("welcome_dm_enabled", True):
        try:
            await send_welcome_dm(context, user, channel)
            dm_sent = True
        except Exception as e:
            logger.error(f"Welcome DM failed for {user.id}: {e}")

    try:
        await context.bot.approve_chat_join_request(chat.id, user.id)
        await approve_join_request_db(chat.id, user.id)
        if dm_sent:
            await increment_dm_count(chat.id)
        logger.info(f"Approved {user.id} for {chat.id} (dm={dm_sent})")
    except Exception as e:
        logger.error(f"Failed to approve {user.id} for {chat.id}: {e}")


async def send_welcome_dm(context, user, channel):
    """Send the welcome DM to a user."""
    user_lang = getattr(user, 'language_code', None)
    welcome_text = get_welcome_for_language(channel, user_lang)
    
    if not welcome_text:
        welcome_text = channel.get("welcome_message") or f"Welcome to {channel.get('chat_title', 'the channel')}! \ud83c\udf89"
    
    text = replace_variables(welcome_text, user=user, channel=channel)
    
    watermark = await get_watermark(channel, channel.get("owner_id", 0))
    if watermark:
        text += watermark

    media_type = channel.get("welcome_media_type")
    media_id = channel.get("welcome_media_file_id")
    
    if media_id and media_type == "photo":
        await context.bot.send_photo(user.id, media_id, caption=text, parse_mode="HTML")
    elif media_id and media_type == "video":
        await context.bot.send_video(user.id, media_id, caption=text, parse_mode="HTML")
    elif media_id and media_type == "document":
        await context.bot.send_document(user.id, media_id, caption=text, parse_mode="HTML")
    else:
        await context.bot.send_message(user.id, text, parse_mode="HTML")
