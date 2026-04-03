"""Broadcast handlers."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import get_owner_channels, create_broadcast, get_broadcast_recipients, update_broadcast_progress, mark_user_blocked, get_broadcast_by_id

logger = logging.getLogger(__name__)


async def handle_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    if data == "broadcast_menu":
        channels = await get_owner_channels(user_id)
        if not channels:
            await query.message.edit_text("\U0001f4e2 No channels. Add me to a channel first!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="main_menu")]]))
            return
        buttons = [[InlineKeyboardButton(ch.get("chat_title", "?")[:30], callback_data=f"bc_ch:{ch['chat_id']}")] for ch in channels]
        buttons.append([InlineKeyboardButton("\u00ab Back", callback_data="main_menu")])
        await query.message.edit_text("\U0001f4e2 <b>Broadcast</b>\nSelect a channel:", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("bc_ch:"):
        chat_id = int(data.split(":")[1])
        context.user_data["bc_setup"] = {"channel_id": chat_id}
        await query.message.edit_text("\U0001f4e2 Send the broadcast message (text, photo, or video):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="broadcast_menu")]]))
    elif data.startswith("bc_send:"):
        bc_id = int(data.split(":")[1])
        bc = await get_broadcast_by_id(bc_id)
        if not bc:
            await query.answer("Broadcast not found!")
            return
        recipients = await get_broadcast_recipients(bc["owner_id"], bc.get("channel_id"))
        sent, failed, blocked = 0, 0, 0
        await update_broadcast_progress(bc_id, 0, 0, 0, "sending")
        for uid in recipients:
            try:
                if bc["content_type"] == "text":
                    await context.bot.send_message(uid, bc["content"], parse_mode="HTML")
                elif bc["content_type"] == "photo":
                    await context.bot.send_photo(uid, bc["media_file_id"], caption=bc.get("caption"), parse_mode="HTML")
                sent += 1
            except Exception as e:
                if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                    blocked += 1
                    await mark_user_blocked(uid)
                else:
                    failed += 1
        await update_broadcast_progress(bc_id, sent, failed, blocked, "completed")
        await query.message.edit_text(f"\U0001f4e2 Broadcast complete!\n\u2705 Sent: {sent}\n\u274c Failed: {failed}\n\U0001f6ab Blocked: {blocked}")


async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setup = context.user_data.pop("bc_setup", None)
    if not setup:
        return
    msg = update.message
    channel_id = setup["channel_id"]
    owner_id = msg.from_user.id
    if msg.photo:
        bc_id = await create_broadcast(owner_id, channel_id, "photo", media_file_id=msg.photo[-1].file_id, caption=msg.caption)
    elif msg.video:
        bc_id = await create_broadcast(owner_id, channel_id, "video", media_file_id=msg.video.file_id, caption=msg.caption)
    else:
        bc_id = await create_broadcast(owner_id, channel_id, "text", content=msg.text)
    recipients = await get_broadcast_recipients(owner_id, channel_id)
    buttons = [
        [InlineKeyboardButton(f"\U0001f4e4 Send to {len(recipients)} users", callback_data=f"bc_send:{bc_id}")],
        [InlineKeyboardButton("\u274c Cancel", callback_data="broadcast_menu")],
    ]
    await msg.reply_text(f"\U0001f4e2 Broadcast ready! Target: {len(recipients)} users.", reply_markup=InlineKeyboardMarkup(buttons))
