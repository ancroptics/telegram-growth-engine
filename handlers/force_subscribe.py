"""Force subscribe management."""
import json
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import (
    get_managed_channel, update_channel_setting,
    mark_force_sub_completed, approve_join_request_db
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
            return
        await query.answer()
        enabled = channel.get("force_subscribe_enabled", False)
        channels = channel.get("force_subscribe_channels") or []
        if isinstance(channels, str):
            channels = json.loads(channels)
        text = (f"\ud83d\udd12 <b>Force Subscribe</b>\n\nStatus: {'\u2705 Enabled' if enabled else '\u274c Disabled'}\nRequired Channels: {len(channels)}\n\n")
        for ch in channels:
            text += f"  \u2022 {ch.get('title', 'Unknown')} (@{ch.get('username', 'N/A')})\n"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=force_subscribe_kb(chat_id, enabled))

    elif data.startswith("fs_toggle:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        new_val = not channel.get("force_subscribe_enabled", False)
        await update_channel_setting(chat_id, force_subscribe_enabled=new_val)
        await query.answer(f"Force Subscribe: {'ON' if new_val else 'OFF'}", show_alert=True)
        update.callback_query.data = f"ch_force_sub:{chat_id}"
        await handle_force_sub_callback(update, context)

    elif data.startswith("fs_add:"):
        chat_id = int(data.split(":")[1])
        context.user_data["fs_add_for"] = chat_id
        await query.answer()
        await query.message.edit_text("\u2795 <b>Add Force Subscribe Channel</b>\n\nForward a message from the channel, or send @username.\n/cancel to abort", parse_mode="HTML")

    elif data.startswith("fs_verify:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        force_channels = channel.get("force_subscribe_channels") or []
        if isinstance(force_channels, str): force_channels = json.loads(force_channels)
        all_joined = True
        for fc in force_channels:
            try:
                member = await context.bot.get_chat_member(fc["chat_id"], user.id)
                if member.status in ("left", "kicked"): all_joined = False; break
            except Exception: all_joined = False; break
        if all_joined:
            try:
                await context.bot.approve_chat_join_request(chat_id, user.id)
                await approve_join_request_db(user.id, chat_id, "force_sub")
                await mark_force_sub_completed(user.id, chat_id)
                await query.answer("\u2705 Verified! Approved.", show_alert=True)
            except Exception as e:
                await query.answer("Error.", show_alert=True)
        else:
            await query.answer("\u274c Join all required channels first!", show_alert=True)
