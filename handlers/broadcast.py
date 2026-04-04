"""Broadcast handler."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import (get_owner_channels, get_channel_users, get_all_user_ids,
    create_broadcast, update_broadcast, mark_user_blocked)
from config import ADMIN_IDS
logger = logging.getLogger(__name__)

async def broadcast_menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    channels = await get_owner_channels(query.from_user.id)
    buttons = [[InlineKeyboardButton(ch.get("chat_title","?"), callback_data=f"bc_channel:{ch['chat_id']}")] for ch in channels]
    if query.from_user.id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("Global Broadcast", callback_data="bc_global")])
    buttons.append([InlineKeyboardButton("Back", callback_data="main_menu")])
    await query.message.edit_text("Select channel to broadcast to:", reply_markup=InlineKeyboardMarkup(buttons))

async def bc_channel_callback(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[1])
    context.user_data["bc_target"] = chat_id
    context.user_data["bc_type"] = "channel"
    await query.message.edit_text("Send message to broadcast (text, photo, or video):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="broadcast_menu")]]))

async def bc_global_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("Admin only!", show_alert=True)
        return
    context.user_data["bc_target"] = "global"
    context.user_data["bc_type"] = "global"
    await query.message.edit_text("Send message for global broadcast:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="broadcast_menu")]]))

async def handle_broadcast_input(update, context):
    target = context.user_data.get("bc_target")
    if not target: return False
    context.user_data.pop("bc_target", None)
    bc_type = context.user_data.pop("bc_type", "channel")
    if bc_type == "global":
        user_ids = await get_all_user_ids()
    else:
        rows = await get_channel_users(target)
        user_ids = [r["user_id"] for r in rows] if rows else []
    if not user_ids:
        await update.message.reply_text("No users to broadcast to.")
        return True
    bc = await create_broadcast(update.effective_user.id, str(target), update.message.text or "(media)")
    sent = failed = 0
    for uid in user_ids:
        try:
            if update.message.photo:
                await context.bot.send_photo(uid, update.message.photo[-1].file_id, caption=update.message.caption)
            elif update.message.video:
                await context.bot.send_video(uid, update.message.video.file_id, caption=update.message.caption)
            else:
                await context.bot.send_message(uid, update.message.text)
            sent += 1
        except Exception as e:
            failed += 1
            if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                await mark_user_blocked(uid)
    if bc:
        await update_broadcast(bc.get("id"), status="done", sent_count=sent, failed_count=failed)
    await update.message.reply_text(f"Broadcast done! Sent: {sent}, Failed: {failed}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="main_menu")]]))
    return True
