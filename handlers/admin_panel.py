"""Admin panel commands and callbacks."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import ban_user, unban_user, set_user_tier, get_global_stats, get_all_owners, get_all_user_ids, get_all_settings, set_setting
from config import Config

logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS or user_id in Config.SUPERADMIN_IDS


async def admin_ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        uid = int(args[0])
        await ban_user(uid)
        await update.message.reply_text(f"\u2705 User {uid} banned.")
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {e}")


async def admin_unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        uid = int(args[0])
        await unban_user(uid)
        await update.message.reply_text(f"\u2705 User {uid} unbanned.")
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {e}")


async def admin_set_tier_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /settier <user_id> <free|premium|business>")
        return
    try:
        uid = int(args[0])
        tier = args[1].lower()
        if tier not in ("free", "premium", "business"):
            await update.message.reply_text("\u274c Tier must be: free, premium, or business")
            return
        await set_user_tier(uid, tier)
        await update.message.reply_text(f"\u2705 User {uid} set to {tier} tier.")
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {e}")


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if not _is_admin(update.effective_user.id):
        await query.message.edit_text("\u274c Admin only.")
        return
    if data == "admin_panel":
        stats = await get_global_stats()
        text = ("\ud83d\udd27 <b>Admin Panel</b>\n\n"
            f"\ud83d\udc65 Users: {stats['total_users']}\n"
            f"\ud83d\udce2 Channels: {stats['active_channels']}\n"
            f"\ud83d\udc64 Owners: {stats['total_owners']}\n"
            f"\ud83d\udcc8 Today: {stats['today_requests']} requests, {stats['today_approved']} approved, {stats['today_dms']} DMs")
        buttons = [
            [InlineKeyboardButton("\ud83d\udc65 All Owners", callback_data="admin_owners"),
             InlineKeyboardButton("\ud83d\udce2 Broadcast All", callback_data="admin_bc")],
            [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="admin_settings")],
            [InlineKeyboardButton("\u00ab Back", callback_data="main_menu")],
        ]
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    elif data == "admin_owners":
        owners = await get_all_owners(20)
        text = "\ud83d\udc65 <b>Recent Owners</b>\n\n"
        for o in owners:
            text += f"\u2022 {o.get('user_id')} \u2014 {o.get('username', 'N/A')} [{o.get('tier', 'free')}]\n"
        if not owners:
            text += "No owners yet."
        await query.message.edit_text(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="admin_panel")]]))
    elif data == "admin_bc":
        context.user_data["admin_broadcast"] = True
        await query.message.edit_text("\ud83d\udce2 Send the message to broadcast to ALL users:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="admin_panel")]]))
    elif data == "admin_settings":
        settings = await get_all_settings()
        text = "\u2699\ufe0f <b>Platform Settings</b>\n\n"
        for k, v in settings.items():
            text += f"<code>{k}</code> = <code>{v}</code>\n"
        if not settings:
            text += "No settings configured."
        context.user_data["editing_setting"] = True
        await query.message.edit_text(text + "\nSend <code>key=value</code> to update:", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="admin_panel")]]))


async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_broadcast"):
        return
    context.user_data.pop("admin_broadcast", None)
    text = update.message.text
    user_ids = await get_all_user_ids()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"\ud83d\udce2 Broadcast complete: {sent} sent, {failed} failed.")


async def admin_setting_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("editing_setting"):
        return
    context.user_data.pop("editing_setting", None)
    text = update.message.text
    if "=" not in text:
        await update.message.reply_text("\u274c Format: key=value")
        return
    key, value = text.split("=", 1)
    await set_setting(key.strip(), value.strip())
    await update.message.reply_text(f"\u2705 Setting <code>{key.strip()}</code> updated.", parse_mode="HTML")
