"""Admin handler."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import get_global_stats, get_all_owners, get_active_channels, ban_owner, unban_owner, set_user_tier
from config import ADMIN_IDS
logger = logging.getLogger(__name__)

def admin_only(func):
    async def wrapper(update, context):
        uid = update.effective_user.id if update.effective_user else 0
        if uid not in ADMIN_IDS:
            if update.callback_query: await update.callback_query.answer("Admin only!", show_alert=True)
            return
        return await func(update, context)
    return wrapper

@admin_only
async def admin_panel_callback(update, context):
    query = update.callback_query
    await query.answer()
    gs = await get_global_stats()
    text = (f"Admin Panel\n\nOwners: {gs['total_owners']}\nChannels: {gs['total_channels']}\n"
            f"Users: {gs['total_users']}\nPremium: {gs['premium_owners']}")
    buttons = [[InlineKeyboardButton("All Channels", callback_data="admin_channels")],
               [InlineKeyboardButton("Back", callback_data="main_menu")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@admin_only
async def admin_channels_callback(update, context):
    query = update.callback_query
    await query.answer()
    channels = await get_active_channels()
    text = f"Active Channels ({len(channels)})\n\n"
    for ch in channels[:20]:
        text += f"{ch.get('chat_title','?')} (owner: {ch.get('owner_id','?')})\n"
    await query.message.edit_text(text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin_panel")]]))

async def ban_command(update, context):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id> [reason]"); return
    uid = int(context.args[0])
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    await ban_owner(uid, reason)
    await update.message.reply_text(f"Banned user {uid}")

async def unban_command(update, context):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>"); return
    await unban_owner(int(context.args[0]))
    await update.message.reply_text(f"Unbanned user {context.args[0]}")

async def setpremium_command(update, context):
    if update.effective_user.id not in ADMIN_IDS: return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setpremium <user_id> <tier> [days]"); return
    uid = int(context.args[0])
    tier = context.args[1]
    days = int(context.args[2]) if len(context.args) > 2 else 30
    await set_user_tier(uid, tier, days)
    await update.message.reply_text(f"Set {uid} to {tier} for {days} days")
