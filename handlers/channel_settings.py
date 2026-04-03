"""Per-channel settings management."""
import json
import logging
from html import escape as html_escape
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import get_managed_channel, update_channel_setting, get_pending_requests, get_owner_channels
from utils.keyboards import channel_manage_kb, channel_settings_kb, channels_list_kb, back_kb
from utils.helpers import format_number

logger = logging.getLogger(__name__)


async def show_channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    channels = await get_owner_channels(user.id)
    if not channels:
        text = ("\ud83d\udce2 <b>My Channels</b>\n\n"
                "No channels connected yet!\n\n"
                "Add me as admin to your channel to get started.")
        kb = back_kb("main_menu")
    else:
        text = f"\ud83d\udce2 <b>My Channels</b> ({len(channels)})\n\n"
        for ch in channels:
            title = html_escape(ch.get("chat_title", "Unknown"))
            approved = ch.get("total_approved", 0)
            active = "\u2705" if ch.get("is_active", True) else "\u23f8"
            text += f"{active} <b>{title}</b> \u2014 \u2705 {format_number(approved)}\n"
        kb = channels_list_kb(channels)

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


async def handle_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("manage_ch:"):
        chat_id = int(data.split(":")[1])
        await query.answer()
        await _show_channel_manage(query, chat_id)

    elif data.startswith("ch_settings:"):
        chat_id = int(data.split(":")[1])
        await query.answer()
        await _show_channel_settings(query, chat_id)

    elif data.startswith("toggle_"):
        parts = data.split(":")
        setting = parts[0].replace("toggle_", "")
        chat_id = int(parts[1])

        channel = await get_managed_channel(chat_id)
        if not channel:
            await query.answer("Channel not found", show_alert=True)
            return

        current = channel.get(setting, False)
        new_val = not current
        await update_channel_setting(chat_id, setting, new_val)

        status = "enabled" if new_val else "disabled"
        await query.answer(f"{setting.replace('_', ' ').title()} {status}!")
        await _show_channel_settings(query, chat_id)

    elif data.startswith("set_welcome:"):
        chat_id = int(data.split(":")[1])
        context.user_data["editing_welcome"] = chat_id
        await query.answer()
        await query.message.edit_text(
            "\ud83d\udcdd <b>Set Welcome Message</b>\n\n"
            "Send the new welcome message. Variables:\n"
            "<code>{first_name}</code> \u2014 User\'s first name\n"
            "<code>{username}</code> \u2014 User\'s username\n"
            "<code>{channel_name}</code> \u2014 Channel title\n"
            "<code>{member_count}</code> \u2014 Member count\n\n"
            "Send your message now:",
            parse_mode="HTML",
            reply_markup=back_kb(f"ch_settings:{chat_id}")
        )

    elif data.startswith("remove_ch:"):
        chat_id = int(data.split(":")[1])
        from database.models import remove_managed_channel
        await remove_managed_channel(chat_id)
        await query.answer("\u2705 Channel removed", show_alert=True)
        await show_channels_list(update, context)


async def _show_channel_manage(query, chat_id):
    channel = await get_managed_channel(chat_id)
    if not channel:
        await query.message.edit_text("Channel not found.", reply_markup=back_kb("my_channels"))
        return

    title = html_escape(channel.get("chat_title", "Unknown"))
    approved = channel.get("total_approved", 0)
    pending_count = len(await get_pending_requests(chat_id, limit=1))
    members = channel.get("member_count", 0)
    dms = channel.get("dm_sent_count", 0)

    auto = "\u2705" if channel.get("auto_approve", True) else "\u274c"
    drip = "\u2705" if channel.get("drip_enabled", False) else "\u274c"
    welcome = "\u2705" if channel.get("welcome_dm_enabled", True) else "\u274c"

    text = (f"\u2699\ufe0f <b>{title}</b>\n\n"
            f"\ud83d\udc65 Members: {format_number(members)}\n"
            f"\u2705 Approved: {format_number(approved)}\n"
            f"\u23f3 Pending: {pending_count}+\n"
            f"\ud83d\udcac DMs Sent: {format_number(dms)}\n\n"
            f"<b>Settings:</b>\n"
            f"Auto-approve: {auto}\n"
            f"Drip mode: {drip}\n"
            f"Welcome DM: {welcome}")

    await query.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=channel_manage_kb(chat_id)
    )


async def _show_channel_settings(query, chat_id):
    channel = await get_managed_channel(chat_id)
    if not channel:
        await query.message.edit_text("Channel not found.", reply_markup=back_kb("my_channels"))
        return

    title = html_escape(channel.get("chat_title", "Unknown"))
    text = f"\u2699\ufe0f <b>Settings for {title}</b>\n\n"

    settings_map = {
        "auto_approve": ("Auto-Approve", channel.get("auto_approve", True)),
        "welcome_dm_enabled": ("Welcome DM", channel.get("welcome_dm_enabled", True)),
        "drip_enabled": ("Drip Mode", channel.get("drip_enabled", False)),
        "watermark_enabled": ("Watermark", channel.get("watermark_enabled", True)),
    }

    for key, (label, val) in settings_map.items():
        icon = "\u2705" if val else "\u274c"
        text += f"{icon} {label}\n"

    await query.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=channel_settings_kb(chat_id, channel)
    )


async def channel_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = context.user_data.get("editing_welcome")
    if not chat_id:
        return False

    new_welcome = update.message.text.strip()
    if not new_welcome:
        await update.message.reply_text("\u26a0\ufe0f Message cannot be empty.")
        return True

    await update_channel_setting(chat_id, "welcome_message", new_welcome)
    context.user_data.pop("editing_welcome", None)

    await update.message.reply_text(
        f"\u2705 Welcome message updated!\n\n"
        f"Preview:\n{html_escape(new_welcome[:200])}",
        parse_mode="HTML",
        reply_markup=back_kb(f"ch_settings:{chat_id}")
    )
    return True
