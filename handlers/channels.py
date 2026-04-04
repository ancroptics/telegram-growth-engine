"""Channel management."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
from telegram.ext import ContextTypes
from database.models import (add_managed_channel, get_managed_channel, get_owner_channels,
    remove_managed_channel, update_channel_setting, get_or_create_owner)
logger = logging.getLogger(__name__)

async def my_channels_callback(update, context):
    query = update.callback_query
    await query.answer()
    channels = await get_owner_channels(query.from_user.id)
    if not channels:
        await query.message.edit_text("No channels yet. Add me as admin to your channel!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="main_menu")]]))
        return
    text = f"My Channels ({len(channels)})\n\n"
    buttons = []
    for ch in channels:
        s = "ON" if ch.get("is_active") else "OFF"
        title = ch.get("chat_title", "Unknown")
        text += f"[{s}] {title}\n"
        buttons.append([InlineKeyboardButton(title, callback_data=f"ch_settings:{ch['chat_id']}")])
    buttons.append([InlineKeyboardButton("Back", callback_data="main_menu")])
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def channel_settings_callback(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[1])
    ch = await get_managed_channel(chat_id)
    if not ch:
        await query.message.edit_text("Channel not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="my_channels")]]))
        return
    title = ch.get("chat_title", "Unknown")
    aa = "ON" if ch.get("auto_approve") else "OFF"
    wd = "ON" if ch.get("welcome_dm_enabled") else "OFF"
    mode = ch.get("approve_mode", "instant")
    text = (f"Settings: {title}\n\nAuto Approve: {aa}\nApprove Mode: {mode}\n"
            f"Welcome DM: {wd}\nTotal Approved: {ch.get('total_approved',0)}\nDMs Sent: {ch.get('total_dm_sent',0)}")
    buttons = [
        [InlineKeyboardButton(f"Toggle Auto-Approve ({aa})", callback_data=f"toggle_approve:{chat_id}")],
        [InlineKeyboardButton(f"Toggle Welcome DM ({wd})", callback_data=f"toggle_welcome:{chat_id}")],
        [InlineKeyboardButton("Edit Welcome Msg", callback_data=f"edit_welcome:{chat_id}")],
        [InlineKeyboardButton("Approve Mode", callback_data=f"approve_mode:{chat_id}")],
        [InlineKeyboardButton("Back", callback_data="my_channels")],
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def toggle_approve_callback(update, context):
    query = update.callback_query
    chat_id = int(query.data.split(":")[1])
    ch = await get_managed_channel(chat_id)
    if ch:
        nv = not ch.get("auto_approve", True)
        await update_channel_setting(chat_id, auto_approve=nv)
        await query.answer(f"Auto-approve: {'ON' if nv else 'OFF'}", show_alert=True)
    query.data = f"ch_settings:{chat_id}"
    await channel_settings_callback(update, context)

async def toggle_welcome_callback(update, context):
    query = update.callback_query
    chat_id = int(query.data.split(":")[1])
    ch = await get_managed_channel(chat_id)
    if ch:
        nv = not ch.get("welcome_dm_enabled", True)
        await update_channel_setting(chat_id, welcome_dm_enabled=nv)
        await query.answer(f"Welcome DM: {'ON' if nv else 'OFF'}", show_alert=True)
    query.data = f"ch_settings:{chat_id}"
    await channel_settings_callback(update, context)

async def edit_welcome_callback(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[1])
    ch = await get_managed_channel(chat_id)
    current = ch.get("welcome_message", "") if ch else ""
    context.user_data["awaiting_welcome_msg"] = chat_id
    await query.message.edit_text(f"Current welcome message:\n{current}\n\nSend new message. Variables: {{user_name}}, {{channel_name}}, {{user_id}}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"ch_settings:{chat_id}")]]))

async def approve_mode_callback(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[1])
    buttons = [
        [InlineKeyboardButton("Instant", callback_data=f"set_mode:instant:{chat_id}")],
        [InlineKeyboardButton("Drip (30s delay)", callback_data=f"set_mode:drip:{chat_id}")],
        [InlineKeyboardButton("Manual", callback_data=f"set_mode:manual:{chat_id}")],
        [InlineKeyboardButton("Back", callback_data=f"ch_settings:{chat_id}")],
    ]
    await query.message.edit_text("Choose approve mode:", reply_markup=InlineKeyboardMarkup(buttons))

async def set_mode_callback(update, context):
    query = update.callback_query
    parts = query.data.split(":")
    mode, chat_id = parts[1], int(parts[2])
    await update_channel_setting(chat_id, approve_mode=mode)
    await query.answer(f"Mode: {mode}", show_alert=True)
    query.data = f"ch_settings:{chat_id}"
    await channel_settings_callback(update, context)

async def handle_my_chat_member(update, context):
    result = update.my_chat_member
    if not result: return
    chat = result.chat
    old = result.old_chat_member
    new = result.new_chat_member
    user = result.from_user
    if new.status in ("administrator","member") and old.status in ("left","kicked"):
        if chat.type in ("channel","supergroup"):
            await get_or_create_owner(user.id, user.username, user.first_name)
            await add_managed_channel(chat.id, chat.title or "Untitled", user.id, chat.type)
            try:
                await context.bot.send_message(user.id, f"Channel Added! {chat.title} is now managed. Use /start to configure.")
            except: pass
    elif new.status in ("left","kicked") and old.status in ("administrator","member"):
        await remove_managed_channel(chat.id)

async def handle_welcome_message_input(update, context):
    chat_id = context.user_data.get("awaiting_welcome_msg")
    if not chat_id: return False
    await update_channel_setting(chat_id, welcome_message=update.message.text)
    context.user_data.pop("awaiting_welcome_msg", None)
    await update.message.reply_text("Welcome message updated!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Channel Settings", callback_data=f"ch_settings:{chat_id}")]]))
    return True
