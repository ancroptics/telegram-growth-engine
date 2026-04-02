"""Broadcast management."""
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import Forbidden
from database.models import (
    get_owner_channels, create_broadcast, get_broadcast_targets,
    update_broadcast_progress, mark_user_blocked, get_broadcasts
)
from utils.keyboards import broadcast_kb, back_kb
from utils.decorators import channel_owner_only
from utils.helpers import format_number, progress_bar

logger = logging.getLogger(__name__)

async def handle_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user

    if data == "broadcast_menu":
        await query.answer()
        channels = await get_owner_channels(user.id)
        text = ("\ud83d\udce3 <b>BROADCAST CENTER</b>\n\n"
                "Send messages to all users who joined through your channels.\n\n")
        if not channels:
            text += "Add a channel first!"
        else:
            text += "Select a channel to broadcast to:"
        kb = []
        for ch in channels:
            kb.append([InlineKeyboardButton(f"\ud83d\udce2 {ch.get('chat_title','?')[:30]}", callback_data=f"bc_select:{ch['chat_id']}")])
        kb.append([InlineKeyboardButton("\ud83d\udcca Broadcast History", callback_data="bc_history")])
        kb.append([InlineKeyboardButton("\u00ab Back", callback_data="main_menu")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("bc_select:"):
        chat_id = int(data.split(":")[1])
        await query.answer()
        targets = await get_broadcast_targets(user.id, "all", chat_id)
        text = (f"\ud83d\udce3 <b>Broadcast Setup</b>\n\n"
                f"\ud83c\udfaf Target: {len(targets)} users\n\n"
                "Send your broadcast message now.\n"
                "Supports: text, photo, video, document.\n\n"
                "/cancel to abort")
        context.user_data["bc_setup"] = {"channel_id": chat_id, "target_count": len(targets)}
        await query.message.edit_text(text, parse_mode="HTML")

    elif data == "bc_history":
        await query.answer()
        broadcasts = await get_broadcasts(user.id, limit=10)
        if not broadcasts:
            text = "\ud83d\udcca No broadcast history."
        else:
            text = "\ud83d\udcca <b>Broadcast History</b>\n\n"
            for bc in broadcasts:
                status_emoji = {'completed': '\u2705', 'sending': '\u23f3', 'scheduled': '\ud83d\udcc5', 'failed': '\u274c'}.get(bc.get('status',''), '\u2753')
                text += (f"{status_emoji} {bc.get('created_at','')[:16]}\n"
                         f"   Sent: {bc.get('sent_count',0)} | Failed: {bc.get('failed_count',0)}\n")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("broadcast_menu"))

    elif data.startswith("bc_confirm:"):
        bc_id = int(data.split(":")[1])
        await query.answer("\u23f3 Starting broadcast...")
        await execute_broadcast(bc_id, user.id, context)
        await query.message.edit_text("\u2705 Broadcast started! Check /broadcasts for progress.", reply_markup=back_kb("broadcast_menu"))

async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setup = context.user_data.get("bc_setup")
    if not setup: return False
    message = update.message
    user = update.effective_user
    if message.text and message.text.startswith("/cancel"):
        del context.user_data["bc_setup"]
        await message.reply_text("\u274c Broadcast cancelled.")
        return True
    # Determine content
    content_type = "text"
    content = message.text or ""
    media_file_id = None
    caption = None
    if message.photo:
        content_type = "photo"
        media_file_id = message.photo[-1].file_id
        caption = message.caption or ""
    elif message.video:
        content_type = "video"
        media_file_id = message.video.file_id
        caption = message.caption or ""
    elif message.document:
        content_type = "document"
        media_file_id = message.document.file_id
        caption = message.caption or ""
    bc_id = await create_broadcast(
        owner_id=user.id, channel_id=setup["channel_id"],
        content_type=content_type, content=content,
        media_file_id=media_file_id, caption=caption,
        target_segment="all"
    )
    del context.user_data["bc_setup"]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u2705 Send Now", callback_data=f"bc_confirm:{bc_id}"), InlineKeyboardButton("\u274c Cancel", callback_data="broadcast_menu")]])
    await message.reply_text(f"\ud83d\udce3 Broadcast ready!\n\nTargets: ~{setup['target_count']} users\nType: {content_type}\n\nConfirm?", reply_markup=kb)
    return True

async def execute_broadcast(bc_id: int, owner_id: int, context: ContextTypes.DEFAULT_TYPE):
    from database.models import get_broadcast_by_id
    bc = await get_broadcast_by_id(bc_id)
    if not bc: return
    targets = await get_broadcast_targets(owner_id, bc.get("target_segment", "all"), bc.get("channel_id"))
    sent = failed = blocked = 0
    await update_broadcast_progress(bc_id, 0, 0, 0, "sending")
    for uid in targets:
        try:
            if bc.get("content_type") == "photo" and bc.get("media_file_id"):
                await context.bot.send_photo(uid, bc["media_file_id"], caption=bc.get("caption", ""), parse_mode="HTML")
            elif bc.get("content_type") == "video" and bc.get("media_file_id"):
                await context.bot.send_video(uid, bc["media_file_id"], caption=bc.get("caption", ""), parse_mode="HTML")
            elif bc.get("content_type") == "document" and bc.get("media_file_id"):
                await context.bot.send_document(uid, bc["media_file_id"], caption=bc.get("caption", ""), parse_mode="HTML")
            else:
                await context.bot.send_message(uid, bc.get("content", ""), parse_mode="HTML")
            sent += 1
        except Forbidden:
            blocked += 1
            await mark_user_blocked(uid)
        except Exception:
            failed += 1
        if sent % 25 == 0:
            await asyncio.sleep(1)
            await update_broadcast_progress(bc_id, sent, failed, blocked, "sending")
    await update_broadcast_progress(bc_id, sent, failed, blocked, "completed")
