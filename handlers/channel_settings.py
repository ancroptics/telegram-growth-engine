"""Channel settings callback handler."""
import logging
from html import escape as html_escape
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import get_owner_channels, get_managed_channel, update_channel_setting, remove_managed_channel

logger = logging.getLogger(__name__)


async def handle_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    if data in ("my_channels", "add_channel"):
        channels = await get_owner_channels(user_id)
        if not channels:
            await query.message.edit_text("\U0001f4ca <b>My Channels</b>\n\nNo channels yet! Add me as admin to a channel.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="main_menu")]]))
            return
        buttons = []
        for ch in channels:
            title = html_escape(ch.get("chat_title", "?"))[:30]
            buttons.append([InlineKeyboardButton(f"\U0001f4e2 {title}", callback_data=f"manage_ch:{ch['chat_id']}")] )
        buttons.append([InlineKeyboardButton("\u00ab Back", callback_data="main_menu")])
        await query.message.edit_text("\U0001f4ca <b>Your Channels</b>\nSelect one to manage:", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("manage_ch:"):
        chat_id = int(data.split(":")[1])
        ch = await get_managed_channel(chat_id)
        if not ch:
            await query.message.edit_text("\u274c Channel not found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="my_channels")]]))
            return
        title = html_escape(ch.get("chat_title", "?"))
        auto = "\u2705" if ch.get("auto_approve") else "\u274c"
        drip = "\u2705" if ch.get("drip_enabled") else "\u274c"
        welcome = "\u2705" if ch.get("welcome_dm_enabled") else "\u274c"
        fsub = "\u2705" if ch.get("force_subscribe_enabled") else "\u274c"
        text = (f"\u2699\ufe0f <b>{title}</b>\n\n"
            f"Auto Approve: {auto}\nDrip Mode: {drip}\nWelcome DM: {welcome}\nForce Subscribe: {fsub}\n"
            f"Members: {ch.get('member_count', 0)} | Approved: {ch.get('total_approved', 0)}")
        buttons = [
            [InlineKeyboardButton(f"{'\U0001f534' if ch.get('auto_approve') else '\U0001f7e2'} Toggle Auto-Approve", callback_data=f"ch_toggle:auto_approve:{chat_id}")],
            [InlineKeyboardButton("\U0001f4ac Edit Welcome", callback_data=f"ch_edit_welcome:{chat_id}"),
             InlineKeyboardButton("\U0001f512 Force Sub", callback_data=f"ch_force_sub:{chat_id}")],
            [InlineKeyboardButton("\U0001f4ca Analytics", callback_data=f"ch_analytics:{chat_id}"),
             InlineKeyboardButton("\U0001f465 Pending", callback_data=f"ch_pending:{chat_id}")],
            [InlineKeyboardButton("\U0001f5d1 Remove", callback_data=f"ch_delete:{chat_id}")],
            [InlineKeyboardButton("\u00ab Back", callback_data="my_channels")],
        ]
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("ch_toggle:"):
        parts = data.split(":")
        field = parts[1]
        chat_id = int(parts[2])
        ch = await get_managed_channel(chat_id)
        if ch:
            new_val = not ch.get(field, False)
            await update_channel_setting(chat_id, **{field: new_val})
            await query.answer(f"{'Enabled' if new_val else 'Disabled'}!")
            update.callback_query.data = f"manage_ch:{chat_id}"
            await handle_channel_callback(update, context)
    elif data.startswith("ch_delete:"):
        chat_id = int(data.split(":")[1])
        buttons = [
            [InlineKeyboardButton("\u2705 Yes, Remove", callback_data=f"ch_confirm_delete:{chat_id}"),
             InlineKeyboardButton("\u274c Cancel", callback_data=f"manage_ch:{chat_id}")],
        ]
        await query.message.edit_text("\u26a0\ufe0f Remove this channel?", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("ch_confirm_delete:"):
        chat_id = int(data.split(":")[1])
        await remove_managed_channel(chat_id)
        await query.answer("Channel removed!")
        update.callback_query.data = "my_channels"
        await handle_channel_callback(update, context)
