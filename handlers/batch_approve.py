"""Batch approval and join request processing."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import (
    get_managed_channel, add_managed_channel, update_channel_setting,
    record_join_request, get_pending_requests, approve_request,
    record_end_user, increment_channel_stat
)
from utils.keyboards import back_kb
from utils.helpers import format_number

logger = logging.getLogger(__name__)


async def process_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming chat join requests."""
    request = update.chat_join_request
    chat = request.chat
    user = request.from_user

    logger.info(f"Join request: user={user.id} chat={chat.id} ({chat.title})")

    # Get or create channel
    channel = await get_managed_channel(chat.id)
    if not channel:
        # Auto-register channel
        invite_link = request.invite_link
        owner_id = invite_link.creator.id if invite_link and invite_link.creator else user.id
        await add_managed_channel(
            chat_id=chat.id,
            chat_title=chat.title or "Unknown",
            owner_id=owner_id,
            chat_type=chat.type
        )
        channel = await get_managed_channel(chat.id)
        logger.info(f"Auto-registered channel: {chat.id} ({chat.title})")

    if not channel:
        logger.error(f"Failed to get/create channel {chat.id}")
        return

    # Record the join request
    await record_join_request(chat.id, user.id, user.username, user.first_name)
    await record_end_user(user.id, user.username, user.first_name, user.language_code)
    await increment_channel_stat(chat.id, "requests_received")

    # Auto-approve if enabled
    if channel.get("auto_approve", False):
        try:
            await context.bot.approve_chat_join_request(chat.id, user.id)
            await approve_request(chat.id, user.id)
            await increment_channel_stat(chat.id, "requests_approved")
            logger.info(f"Auto-approved: user={user.id} chat={chat.id}")

            # Send welcome DM if enabled
            if channel.get("welcome_dm_enabled", False):
                welcome_msg = channel.get("welcome_message", "")
                if welcome_msg:
                    try:
                        welcome_msg = welcome_msg.replace("{first_name}", user.first_name or "")
                        welcome_msg = welcome_msg.replace("{username}", f"@{user.username}" if user.username else "")
                        welcome_msg = welcome_msg.replace("{channel_name}", chat.title or "")

                        media_type = channel.get("welcome_media_type")
                        media_file_id = channel.get("welcome_media_file_id")

                        if media_type == "photo" and media_file_id:
                            await context.bot.send_photo(user.id, media_file_id, caption=welcome_msg, parse_mode="HTML")
                        elif media_type == "video" and media_file_id:
                            await context.bot.send_video(user.id, media_file_id, caption=welcome_msg, parse_mode="HTML")
                        else:
                            await context.bot.send_message(user.id, welcome_msg, parse_mode="HTML")

                        await increment_channel_stat(chat.id, "dms_sent")
                    except Exception as e:
                        logger.error(f"Failed to send welcome DM to {user.id}: {e}")
        except Exception as e:
            logger.error(f"Failed to auto-approve {user.id} in {chat.id}: {e}")
    else:
        logger.info(f"Queued pending: user={user.id} chat={chat.id}")


async def handle_batch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle batch approve and pending request callbacks."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("ch_pending:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel:
            await query.message.edit_text("Channel not found.", reply_markup=back_kb("my_channels"))
            return
        pending = await get_pending_requests(chat_id)
        text = (f"📋 <b>Pending Requests</b>\n"
                f"Channel: {channel.get('chat_title', '?')}\n\n")
        if not pending:
            text += "No pending requests! ✨"
        else:
            text += f"Total pending: {len(pending)}\n\n"
            for p in pending[:20]:
                name = p.get('first_name', 'Unknown')
                uname = f"@{p['username']}" if p.get('username') else ''
                text += f"• {name} {uname}\n"
            if len(pending) > 20:
                text += f"\n... and {len(pending) - 20} more"
        kb = []
        if pending:
            kb.append([InlineKeyboardButton(f"✅ Approve All ({len(pending)})", callback_data=f"batch_approve:{chat_id}")])
        kb.append([InlineKeyboardButton("« Back", callback_data=f"manage_ch:{chat_id}")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("batch_approve:"):
        chat_id = int(data.split(":")[1])
        pending = await get_pending_requests(chat_id)
        approved = 0
        failed = 0
        for p in pending:
            try:
                uid = p.get("user_id")
                await context.bot.approve_chat_join_request(chat_id, uid)
                await approve_request(chat_id, uid)
                approved += 1
            except Exception as e:
                failed += 1
                logger.error(f"Batch approve failed for {uid}: {e}")
        await increment_channel_stat(chat_id, "requests_approved", approved)
        await query.message.edit_text(
            f"✅ Batch approve complete!\n\n"
            f"Approved: {approved}\nFailed: {failed}",
            reply_markup=back_kb(f"manage_ch:{chat_id}")
        )
