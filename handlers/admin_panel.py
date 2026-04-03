from html import escape as html_escape
"""Superadmin panel."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_global_stats, get_all_owners, ban_user, unban_user, set_user_tier
from utils.keyboards import admin_panel_kb, back_kb
from utils.decorators import superadmin_only
from utils.helpers import format_number

logger = logging.getLogger(__name__)

@superadmin_only
async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "superadmin":
        stats = await get_global_stats()
        text = (f"🔒 <b>SUPERADMIN PANEL</b>\n\n"
                f"👥 Total Users: {format_number(stats.get('total_users', 0))}\n"
                f"📢 Total Channels: {format_number(stats.get('total_channels', 0))}\n"
                f"✅ Total Approved: {format_number(stats.get('total_approved', 0))}\n"
                f"💬 Total DMs: {format_number(stats.get('total_dms', 0))}\n\n"
                f"💎 Premium: {stats.get('premium_users', 0)}\n"
                f"💼 Business: {stats.get('business_users', 0)}")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_panel_kb())

    elif data == "sa_users":
        owners = await get_all_owners(limit=20)
        text = "👥 <b>Top Users</b>\n\n"
        for o in owners:
            text += (f"• {html_escape(o.get('full_name','?')[:20])} (ID: {o['user_id']}) "
                     f"— {o.get('tier','free')} | {o.get('channel_count',0)} ch\n")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("superadmin"))

    elif data == "sa_broadcast":
        context.user_data["admin_broadcast"] = True
        await query.message.edit_text("📣 <b>Global Broadcast</b>\n\nSend the message to broadcast to ALL users.\n/cancel to abort", parse_mode="HTML")

@superadmin_only
async def admin_ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /ban {user_id}")
        return
    try:
        uid = int(context.args[0])
        await ban_user(uid)
        await update.message.reply_text(f"✅ User {uid} banned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

@superadmin_only
async def admin_unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /unban {user_id}")
        return
    try:
        uid = int(context.args[0])
        await unban_user(uid)
        await update.message.reply_text(f"✅ User {uid} unbanned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

@superadmin_only
async def admin_set_tier_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /settier {user_id} {free|premium|business}")
        return
    try:
        uid = int(context.args[0])
        tier = context.args[1].lower()
        if tier not in ("free", "premium", "business"):
            await update.message.reply_text("Invalid tier.")
            return
        await set_user_tier(uid, tier)
        await update.message.reply_text(f"✅ User {uid} set to {tier}.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_broadcast"): return False
    message = update.message
    if message.text and message.text.startswith("/cancel"):
        del context.user_data["admin_broadcast"]
        await message.reply_text("❌ Cancelled.")
        return True
    del context.user_data["admin_broadcast"]
    from database.models import get_all_user_ids
    from telegram.error import Forbidden
    user_ids = await get_all_user_ids()
    sent = failed = 0
    import asyncio
    for uid in user_ids:
        try:
            await context.bot.forward_message(uid, message.chat_id, message.message_id)
            sent += 1
        except Forbidden: failed += 1
        except Exception: failed += 1
        if sent % 25 == 0: await asyncio.sleep(1)
    await message.reply_text(f"📣 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}")
    return True
