"""Superadmin panel with full settings management."""
from html import escape as html_escape
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import (
    get_global_stats, get_all_owners, ban_user, unban_user, set_user_tier,
    get_all_settings, get_setting, set_setting, get_all_user_ids, get_owner_channels
)
from utils.decorators import superadmin_only
from utils.helpers import format_number

logger = logging.getLogger(__name__)


def admin_panel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83d\udcca Stats", callback_data="sa_stats"),
         InlineKeyboardButton("\ud83d\udc65 Users", callback_data="sa_users")],
        [InlineKeyboardButton("\ud83d\udce2 Channels", callback_data="sa_channels"),
         InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="sa_settings")],
        [InlineKeyboardButton("\ud83d\udce3 Broadcast All", callback_data="sa_broadcast")],
        [InlineKeyboardButton("\ud83d\udd27 System", callback_data="sa_system")],
        [InlineKeyboardButton("\u00ab Back", callback_data="main_menu")]
    ])


def settings_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83d\udcac Support Username", callback_data="sa_edit:support_username")],
        [InlineKeyboardButton("\ud83d\udc4b Default Welcome", callback_data="sa_edit:default_welcome")],
        [InlineKeyboardButton("\ud83d\udd27 Maintenance Mode", callback_data="sa_edit:maintenance_mode")],
        [InlineKeyboardButton("\u00ab Back", callback_data="superadmin")]
    ])


def tiers_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83c\udd93 Free", callback_data="sa_tier_help:free"),
         InlineKeyboardButton("\ud83d\udc8e Premium", callback_data="sa_tier_help:premium")],
        [InlineKeyboardButton("\ud83d\udcbc Business", callback_data="sa_tier_help:business")],
        [InlineKeyboardButton("\u00ab Back", callback_data="superadmin")]
    ])


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all admin panel callbacks."""
    query = update.callback_query
    data = query.data
    user = update.effective_user

    from config import Config
    if user.id not in Config.SUPERADMIN_IDS:
        await query.answer("\u26d4 Not authorized", show_alert=True)
        return

    if data in ("admin_panel", "superadmin"):
        await query.answer()
        await query.message.edit_text(
            "\ud83d\udd10 <b>Superadmin Panel</b>\n\nSelect an option:",
            parse_mode="HTML", reply_markup=admin_panel_kb()
        )

    elif data == "sa_stats":
        await query.answer()
        try:
            stats = await get_global_stats()
            text = ("\ud83d\udcca <b>Platform Statistics</b>\n\n"
                    f"\ud83d\udc65 Users: {format_number(stats.get('total_users', 0))}\n"
                    f"\ud83d\udce2 Channels: {format_number(stats.get('total_channels', 0))}\n"
                    f"\ud83d\udc64 Owners: {format_number(stats.get('total_owners', 0))}\n"
                    f"\u23f3 Pending: {stats.get('total_pending', 0)}\n"
                    f"\u2705 Approved Today: {stats.get('approved_today', 0)}")
        except Exception as e:
            text = f"\ud83d\udcca <b>Stats</b>\n\n\u26a0\ufe0f Error: {e}"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\ud83d\udd04 Refresh", callback_data="sa_stats")],
            [InlineKeyboardButton("\u00ab Back", callback_data="superadmin")]
        ]))

    elif data == "sa_users":
        await query.answer()
        try:
            owners = await get_all_owners()
            text = "\ud83d\udc65 <b>Channel Owners</b>\n\n"
            if not owners:
                text += "No owners yet."
            else:
                for o in owners[:20]:
                    uid = o.get("user_id", "?")
                    tier = o.get("tier", "free")
                    banned = "\ud83d\udeab" if o.get("is_banned") else ""
                    text += f"\u2022 <code>{uid}</code> [{tier}] {banned}\n"
                if len(owners) > 20:
                    text += f"\n... and {len(owners) - 20} more"
        except Exception as e:
            text = f"\ud83d\udc65 <b>Users</b>\n\n\u26a0\ufe0f Error: {e}"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\ud83d\udd04 Refresh", callback_data="sa_users")],
            [InlineKeyboardButton("\u00ab Back", callback_data="superadmin")]
        ]))

    elif data == "sa_channels":
        await query.answer()
        try:
            from database.connection import Database
            channels = await Database.fetch(
                "SELECT mc.*, co.username as owner_username FROM managed_channels mc "
                "LEFT JOIN channel_owners co ON mc.owner_id = co.user_id "
                "ORDER BY mc.created_at DESC LIMIT 25"
            )
            text = "\ud83d\udce2 <b>All Channels</b>\n\n"
            if not channels:
                text += "No channels registered."
            else:
                for ch in channels[:20]:
                    title = html_escape(ch.get("chat_title", "?"))
                    cid = ch.get("chat_id", "?")
                    owner = ch.get("owner_username") or str(ch.get("owner_id", "?"))
                    approved = ch.get("total_approved", 0)
                    text += f"\u2022 <b>{title}</b>\n  ID: <code>{cid}</code> | Owner: {owner} | \u2705 {approved}\n"
        except Exception as e:
            text = f"\ud83d\udce2 <b>Channels</b>\n\n\u26a0\ufe0f Error: {e}"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\u00ab Back", callback_data="superadmin")]
        ]))

    elif data == "sa_settings":
        await query.answer()
        try:
            settings = await get_all_settings()
            text = "\u2699\ufe0f <b>Platform Settings</b>\n\n"
            if not settings:
                text += "No settings configured yet."
            else:
                for k, v in settings.items():
                    text += f"\u2022 <code>{k}</code> = {html_escape(str(v)[:50])}\n"
        except Exception as e:
            text = f"\u2699\ufe0f <b>Settings</b>\n\n\u26a0\ufe0f Error: {e}"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=settings_kb())

    elif data.startswith("sa_edit:"):
        key = data.split(":", 1)[1]
        current = await get_setting(key, "(not set)")
        context.user_data["editing_setting"] = key
        text = (f"\u270f\ufe0f <b>Edit: {key}</b>\n\n"
                f"Current: <code>{html_escape(str(current))}</code>\n\nSend the new value:")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\u274c Cancel", callback_data="sa_settings")]
        ]))

    elif data == "sa_broadcast":
        await query.answer()
        context.user_data["admin_broadcast"] = True
        text = "\ud83d\udce3 <b>Global Broadcast</b>\n\nSend a message to ALL bot users.\nType your message now:"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\u274c Cancel", callback_data="superadmin")]
        ]))

    elif data == "sa_system":
        await query.answer()
        from database.connection import Database
        try:
            db_ok = await Database.fetchval("SELECT 1")
            db_status = "\u2705 Connected" if db_ok else "\u274c Error"
        except:
            db_status = "\u274c Disconnected"
        text = f"\ud83d\udd27 <b>System Status</b>\n\n\ud83d\uddc4 Database: {db_status}\n\ud83e\udd16 Bot: \u2705 Running"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\u00ab Back", callback_data="superadmin")]
        ]))

    elif data == "noop":
        await query.answer()


@superadmin_only
async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_broadcast"):
        return False
    message = update.message
    if message.text and message.text.startswith("/cancel"):
        context.user_data.pop("admin_broadcast", None)
        await message.reply_text("\u274c Broadcast cancelled.")
        return True
    context.user_data.pop("admin_broadcast", None)
    user_ids = await get_all_user_ids()
    sent = failed = 0
    import asyncio
    from telegram.error import Forbidden
    status_msg = await message.reply_text(f"\ud83d\udce3 Broadcasting to {len(user_ids)} users...")
    for uid in user_ids:
        try:
            if message.photo:
                await context.bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption, parse_mode="HTML")
            elif message.video:
                await context.bot.send_video(uid, message.video.file_id, caption=message.caption, parse_mode="HTML")
            else:
                await context.bot.send_message(uid, message.text, parse_mode="HTML")
            sent += 1
        except Forbidden:
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status_msg.edit_text(f"\u2705 Broadcast complete!\n\ud83d\udce8 Sent: {sent}\n\u274c Failed: {failed}")
    return True


@superadmin_only
async def admin_setting_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("editing_setting")
    if not key:
        return False
    message = update.message
    if message.text and message.text.startswith("/cancel"):
        context.user_data.pop("editing_setting", None)
        await message.reply_text("\u274c Cancelled.")
        return True
    value = message.text.strip() if message.text else ""
    await set_setting(key, value)
    context.user_data.pop("editing_setting", None)
    await message.reply_text(f"\u2705 Setting <b>{key}</b> updated to: <code>{html_escape(value)}</code>", parse_mode="HTML")
    return True


async def admin_ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import Config
    if update.effective_user.id not in Config.SUPERADMIN_IDS:
        return await update.message.reply_text("\u26d4 Superadmin only.")
    if not context.args:
        return await update.message.reply_text("Usage: /ban {user_id}")
    try:
        uid = int(context.args[0])
        await ban_user(uid)
        await update.message.reply_text(f"\ud83d\udeab User {uid} banned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")


async def admin_unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import Config
    if update.effective_user.id not in Config.SUPERADMIN_IDS:
        return await update.message.reply_text("\u26d4 Superadmin only.")
    if not context.args:
        return await update.message.reply_text("Usage: /unban {user_id}")
    try:
        uid = int(context.args[0])
        await unban_user(uid)
        await update.message.reply_text(f"\u2705 User {uid} unbanned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")


async def admin_set_tier_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import Config
    if update.effective_user.id not in Config.SUPERADMIN_IDS:
        return await update.message.reply_text("\u26d4 Superadmin only.")
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /settier {user_id} {free|premium|business}")
    try:
        uid = int(context.args[0])
        tier = context.args[1].lower()
        if tier not in ("free", "premium", "business"):
            return await update.message.reply_text("Tier must be: free, premium, or business")
        await set_user_tier(uid, tier)
        await update.message.reply_text(f"\u2705 User {uid} tier set to {tier}.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
