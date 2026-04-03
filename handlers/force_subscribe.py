"""Force subscribe handlers."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import (
    get_force_sub_channels, add_force_sub_channel, remove_force_sub_channel,
    mark_force_sub_completed, approve_join_request_db, update_channel_stats
)

logger = logging.getLogger(__name__)


async def handle_force_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("fs_verify:"):
        chat_id = int(data.split(":")[1])
        user = update.effective_user
        channels = await get_force_sub_channels(chat_id)
        all_joined = True
        for fc in channels:
            try:
                fc_id = fc if isinstance(fc, (int, str)) else fc.get("chat_id", fc.get("username"))
                if isinstance(fc_id, str) and not fc_id.startswith("@"):
                    fc_id = f"@{fc_id}"
                member = await context.bot.get_chat_member(fc_id, user.id)
                if member.status in ("left", "kicked"):
                    all_joined = False
                    break
            except Exception:
                pass
        if all_joined:
            try:
                await context.bot.approve_chat_join_request(chat_id, user.id)
                await approve_join_request_db(user.id, chat_id, method="force_sub")
                await mark_force_sub_completed(user.id, chat_id)
                await update_channel_stats(chat_id, approved=1)
                await query.message.edit_text("\u2705 Verified! You've been approved. Welcome! \ud83c\udf89")
            except Exception as e:
                logger.error(f"Force sub approve error: {e}")
                await query.message.edit_text("\u2705 Verified! You should be approved shortly.")
        else:
            await query.answer("\u274c You haven't joined all required channels yet!", show_alert=True)
    elif data.startswith("ch_force_sub:"):
        chat_id = int(data.split(":")[1])
        channels = await get_force_sub_channels(chat_id)
        text = f"\ud83d\udd12 <b>Force Subscribe</b>\n\nRequired channels: {len(channels)}\n"
        for i, fc in enumerate(channels):
            name = fc if isinstance(fc, str) else fc.get("username", "?")
            text += f"  {i+1}. {name}\n"
        buttons = [[InlineKeyboardButton("\u2795 Add Channel", callback_data=f"fs_add:{chat_id}")]]
        if channels:
            buttons.append([InlineKeyboardButton("\u2796 Remove Last", callback_data=f"fs_remove:{chat_id}")])
        buttons.append([InlineKeyboardButton("\u00ab Back", callback_data=f"manage_ch:{chat_id}")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("fs_add:"):
        chat_id = int(data.split(":")[1])
        context.user_data["fs_add_for"] = chat_id
        await query.message.edit_text("Send the @username of the channel to add as a force subscribe requirement:")
    elif data.startswith("fs_remove:"):
        chat_id = int(data.split(":")[1])
        channels = await get_force_sub_channels(chat_id)
        if channels:
            last = channels[-1]
            await remove_force_sub_channel(chat_id, last)
            await query.answer(f"Removed")
        update.callback_query.data = f"ch_force_sub:{chat_id}"
        await handle_force_sub_callback(update, context)


async def handle_force_sub_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.pop("fs_add_for", None)
    if not chat_id:
        return
    username = update.message.text.strip().lstrip("@")
    await add_force_sub_channel(chat_id, username)
    await update.message.reply_text(f"\u2705 Added @{username} as force subscribe channel.")
