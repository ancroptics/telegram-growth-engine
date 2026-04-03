from html import escape as html_escape
"""Channel settings and management."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import (
    get_owner_channels, get_managed_channel, update_channel_setting,
    remove_managed_channel, get_owner_tier
)
from utils.keyboards import channels_list_kb, channel_manage_kb, channel_settings_kb, back_kb
from utils.constants import TIER_LIMITS
from utils.helpers import format_number

logger = logging.getLogger(__name__)

async def show_channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE, is_command=False):
    user = update.effective_user
    channels = await get_owner_channels(user.id)
    tier = await get_owner_tier(user.id)
    max_ch = TIER_LIMITS.get(tier, {}).get("max_channels", 1)
    text = (f"📢 <b>MY CHANNELS</b> ({len(channels)}/{max_ch})\n\n")
    if not channels:
        text += "No channels yet. Add bot as admin to a channel!"
    else:
        for ch in channels:
            status = '✅' if ch.get('auto_approve') else '⏸'
            text += f"{status} {html_escape(ch.get('chat_title','?')[:25])} — {format_number(ch.get('member_count',0))} members\n"
    if is_command:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=channels_list_kb(channels))
    else:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=channels_list_kb(channels))

async def handle_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user

    if data == "my_channels":
        await query.answer()
        await show_channels_list(update, context)

    elif data == "add_channel":
        await query.answer()
        text = ("➕ <b>Add Channel</b>\n\n"
                "1. Add this bot to your channel as <b>admin</b>\n"
                "2. Grant permission: <b>Invite Users via Link</b>\n"
                "3. Enable <b>Approve New Members</b> in channel settings\n\n"
                "The bot will detect the channel automatically!")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("my_channels"))

    elif data.startswith("manage_ch:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel:
            await query.answer("Channel not found", show_alert=True)
            return
        await query.answer()
        auto = '✅ ON' if channel.get('auto_approve') else '❌ OFF'
        dm = '✅ ON' if channel.get('welcome_dm_enabled') else '❌ OFF'
        text = (f"📢 <b>{html_escape(channel.get('chat_title',''))}</b>\n\n"
                f"👥 Members: {format_number(channel.get('member_count',0))}\n"
                f"✅ Total Approved: {format_number(channel.get('total_approved',0))}\n"
                f"💬 DMs Sent: {format_number(channel.get('total_dms_sent',0))}\n\n"
                f"Auto-Approve: {auto}\n"
                f"Welcome DM: {dm}")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=channel_manage_kb(chat_id))

    elif data.startswith("ch_settings:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        await query.answer()
        text = f"⚙️ <b>Settings: {html_escape(channel.get('chat_title',''))}</b>\n\nToggle features below:"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=channel_settings_kb(chat_id, channel))

    elif data.startswith("ch_toggle:"):
        parts = data.split(":")
        chat_id = int(parts[1])
        field = parts[2]
        channel = await get_managed_channel(chat_id)
        if not channel: return
        allowed = ["auto_approve", "welcome_dm_enabled", "drip_enabled", "force_subscribe_enabled"]
        if field not in allowed:
            await query.answer("Invalid field", show_alert=True)
            return
        new_val = not channel.get(field, False)
        await update_channel_setting(chat_id, **{field: new_val})
        await query.answer(f"{field}: {'ON' if new_val else 'OFF'}")
        update.callback_query.data = f"ch_settings:{chat_id}"
        await handle_channel_callback(update, context)

    elif data.startswith("ch_delete:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        await query.answer()
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⚠️ Yes, Remove", callback_data=f"ch_confirm_delete:{chat_id}"), InlineKeyboardButton("❌ Cancel", callback_data=f"manage_ch:{chat_id}")]])
        await query.message.edit_text(f"⚠️ Remove <b>{html_escape(channel.get('chat_title',''))}</b>?\nThis deletes all data.", parse_mode="HTML", reply_markup=kb)

    elif data.startswith("ch_confirm_delete:"):
        chat_id = int(data.split(":")[1])
        await remove_managed_channel(chat_id)
        await query.answer("✅ Channel removed", show_alert=True)
        await show_channels_list(update, context)
