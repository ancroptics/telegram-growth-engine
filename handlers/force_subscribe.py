"""Force subscribe management."""
import json
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import (
    get_managed_channel, update_channel_setting,
    mark_force_sub_completed, approve_join_request_db,
    update_channel_stats
)
from utils.keyboards import force_subscribe_kb, back_kb
from utils.decorators import premium_required

logger = logging.getLogger(__name__)

async def handle_force_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user

    if data.startswith("ch_force_sub:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel:
            await query.answer("Channel not found", show_alert=True)
            return
        await query.answer()
        enabled = channel.get("force_subscribe_enabled", False)
        channels = channel.get("force_subscribe_channels") or []
        if isinstance(channels, str):
            try: channels = json.loads(channels)
            except: channels = []
        text = (f"\U0001f512 <b>Force Subscribe</b>\n\n"
                f"Status: {'\u2705 Enabled' if enabled else '\u274c Disabled'}\n"
                f"Required Channels: {len(channels)}\n\n")
        for i, ch in enumerate(channels):
            text += f"  {i+1}. {ch.get('title', 'Unknown')} (@{ch.get('username', 'N/A')})\n"
        if not channels:
            text += "  No channels added yet.\n"
        text += "\nUsers must join all listed channels before being approved."
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=force_subscribe_kb(chat_id, enabled))

    elif data.startswith("fs_toggle:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel:
            await query.answer("Channel not found", show_alert=True)
            return
        new_val = not channel.get("force_subscribe_enabled", False)
        await update_channel_setting(chat_id, force_subscribe_enabled=new_val)
        await query.answer(f"Force Subscribe: {'ON' if new_val else 'OFF'}", show_alert=True)
        query.data = f"ch_force_sub:{chat_id}"
        await handle_force_sub_callback(update, context)

    elif data.startswith("fs_add:"):
        chat_id = int(data.split(":")[1])
        context.user_data["fs_add_for"] = chat_id
        await query.answer()
        await query.message.edit_text(
            "\u2795 <b>Add Force Subscribe Channel</b>\n\n"
            "Send the @username of the channel (e.g. @mychannel).\n"
            "The bot must be admin in that channel.\n\n"
            "/cancel to abort",
            parse_mode="HTML"
        )

    elif data.startswith("fs_verify:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel:
            await query.answer("Channel not found.", show_alert=True)
            return
        force_channels = channel.get("force_subscribe_channels") or []
        if isinstance(force_channels, str):
            try: force_channels = json.loads(force_channels)
            except: force_channels = []
        all_joined = True
        for fc in force_channels:
            try:
                fc_id = fc.get("chat_id")
                if not fc_id:
                    fc_id = f"@{fc.get('username', '')}"
                member = await context.bot.get_chat_member(fc_id, user.id)
                if member.status in ("left", "kicked", "restricted"):
                    all_joined = False
                    break
            except Exception as e:
                logger.warning(f"Force sub check error for {fc}: {e}")
                all_joined = False
                break
        if all_joined:
            try:
                await context.bot.approve_chat_join_request(chat_id, user.id)
                await approve_join_request_db(user.id, chat_id, "force_sub")
                await mark_force_sub_completed(user.id, chat_id)
                await update_channel_stats(chat_id, approved=1)
                await query.answer("\u2705 Verified! You have been approved.", show_alert=True)
                await query.message.edit_text("\u2705 <b>Verified!</b>\n\nYou have been approved to join the channel. Welcome!", parse_mode="HTML")
            except Exception as e:
                logger.error(f"Force sub approve error: {e}")
                await query.answer("\u274c Error approving. The join request may have expired. Try joining again.", show_alert=True)
        else:
            await query.answer("\u274c Please join ALL required channels first, then try again!", show_alert=True)

    elif data.startswith("fs_remove:"):
        parts = data.split(":")
        chat_id = int(parts[1])
        idx = int(parts[2])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        channels = channel.get("force_subscribe_channels") or []
        if isinstance(channels, str):
            try: channels = json.loads(channels)
            except: channels = []
        if 0 <= idx < len(channels):
            removed = channels.pop(idx)
            await update_channel_setting(chat_id, force_subscribe_channels=json.dumps(channels))
            await query.answer(f"Removed {removed.get('title', 'channel')}", show_alert=True)
        query.data = f"ch_force_sub:{chat_id}"
        await handle_force_sub_callback(update, context)

async def handle_force_sub_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message when user is adding a force-sub channel."""
    chat_id = context.user_data.get("fs_add_for")
    if not chat_id:
        return False
    message = update.message
    if message.text and message.text.startswith("/cancel"):
        del context.user_data["fs_add_for"]
        await message.reply_text("\u274c Cancelled.")
        return True
    if not message.text:
        await message.reply_text("Please send a channel @username.")
        return True
    username = message.text.strip().lstrip("@")
    if not username:
        await message.reply_text("Invalid username. Send @username of the channel.")
        return True
    try:
        chat_info = await context.bot.get_chat(f"@{username}")
        fc_entry = {
            "chat_id": chat_info.id,
            "username": username,
            "title": chat_info.title or username
        }
    except Exception as e:
        logger.error(f"Force sub add error: {e}")
        await message.reply_text(f"\u274c Could not find @{username}. Make sure:\n1. The channel exists\n2. The bot is admin in that channel")
        return True
    channel = await get_managed_channel(chat_id)
    if not channel:
        del context.user_data["fs_add_for"]
        await message.reply_text("\u274c Channel not found.")
        return True
    channels = channel.get("force_subscribe_channels") or []
    if isinstance(channels, str):
        try: channels = json.loads(channels)
        except: channels = []
    existing_ids = [c.get("chat_id") for c in channels]
    if fc_entry["chat_id"] in existing_ids:
        await message.reply_text(f"\u26a0\ufe0f @{username} is already in the list.")
        del context.user_data["fs_add_for"]
        return True
    channels.append(fc_entry)
    await update_channel_setting(chat_id, force_subscribe_channels=json.dumps(channels))
    del context.user_data["fs_add_for"]
    await message.reply_text(f"\u2705 Added @{username} ({chat_info.title}) to force subscribe list!")
    return True
