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
from utils.keyboards import admin_panel_kb

logger = logging.getLogger(__name__)


@superadmin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\ud83d\udd10 <b>Superadmin Panel</b>\n\nSelect an option:",
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            parse_mode="HTML",
            reply_markup=admin_panel_kb()
        )

    elif data == "sa_stats":
        await query.answer()
        try:
            stats = await get_global_stats()
            text = ("\ud83d\udcca <b>Platform Statistics</b>\n\n"
                    f"\ud83d\udc65 Total Users: {format_number(stats.get('total_users', 0))}\n"
                    f"\ud83d\udce2 Active Channels: {format_number(stats.get('total_channels', 0))}\n"
                    f"\ud83d\udc64 Channel Owners: {format_number(stats.get('total_owners', 0))}\n\n"
                    f"<b>Today:</b>\n"
                    f"\u23f3 Pending: {stats.get('total_pending', 0)}\n"
                    f"\u2705 Approved Today: {stats.get('approved_today', 0)}")
        except Exception as e:
            text = f"\ud83d\udcca <b>Stats</b>\n\n\u26a0\ufe0f Error loading stats: {e}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="admin_panel")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

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
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("\ud83d\udeab Ban User", callback_data="sa_ban"),
             InlineKeyboardButton("\u2705 Unban User", callback_data="sa_unban")],
            [InlineKeyboardButton("\ud83c\udfc6 Set Tier", callback_data="sa_set_tier")],
            [InlineKeyboardButton("\u00ab Back", callback_data="admin_panel")]
        ])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

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
                    owner = ch.get("owner_username") or ch.get("owner_id", "?")
                    approved = ch.get("total_approved", 0)
                    active = "\u2705" if ch.get("is_active", True) else "\u274c"
                    text += f"{active} <b>{title}</b>\n  ID: <code>{cid}</code> | Owner: @{owner} | \u2705 {approved}\n"
                if len(channels) > 20:
                    text += f"\n... and {len(channels) - 20} more"
        except Exception as e:
            text = f"\ud83d\udce2 <b>Channels</b>\n\n\u26a0\ufe0f Error: {e}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="admin_panel")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_settings":
        await query.answer()
        try:
            settings = await get_all_settings()
            text = "\u2699\ufe0f <b>Platform Settings</b>\n\n"
            if not settings:
                text += "No settings configured yet.\n\nDefault settings will be used."
            else:
                for k, v in settings.items():
                    display_v = v if len(str(v)) < 50 else str(v)[:47] + "..."
                    text += f"\u2022 <code>{k}</code> = {html_escape(str(display_v))}\n"
            text += "\n\nTap a setting to edit:"
        except Exception as e:
            text = f"\u2699\ufe0f <b>Settings</b>\n\n\u26a0\ufe0f Error: {e}"
            settings = {}
        kb = []
        editable = [
            ("support_username", "\ud83d\udcac Support Username"),
            ("welcome_text", "\ud83d\udc4b Default Welcome"),
            ("maintenance_mode", "\ud83d\udd27 Maintenance Mode"),
            ("max_channels_free", "\ud83d\udce2 Max Channels (Free)"),
            ("max_channels_premium", "\ud83d\udce2 Max Channels (Premium)"),
        ]
        for key, label in editable:
            kb.append([InlineKeyboardButton(label, callback_data=f"sa_edit:{key}")])
        kb.append([InlineKeyboardButton("\u00ab Back", callback_data="admin_panel")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("sa_edit:"):
        key = data.split(":", 1)[1]
        try:
            current = await get_setting(key, "(not set)")
        except:
            current = "(not set)"
        context.user_data["admin_editing"] = key
        text = (f"\u270f\ufe0f <b>Edit Setting</b>\n\n"
                f"Key: <code>{key}</code>\n"
                f"Current: {html_escape(str(current))}\n\n"
                f"Send the new value:")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="sa_settings")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_ban":
        context.user_data["admin_action"] = "ban"
        text = "\ud83d\udeab <b>Ban User</b>\n\nSend the user ID to ban:"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="sa_users")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_unban":
        context.user_data["admin_action"] = "unban"
        text = "\u2705 <b>Unban User</b>\n\nSend the user ID to unban:"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="sa_users")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_set_tier":
        context.user_data["admin_action"] = "set_tier"
        text = "\ud83c\udfc6 <b>Set User Tier</b>\n\nSend: <code>user_id tier_name</code>\nExample: <code>123456 premium</code>"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="sa_users")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_broadcast":
        context.user_data["admin_action"] = "broadcast_all"
        text = "\ud83d\udce3 <b>Broadcast to All Users</b>\n\nSend the message to broadcast to all bot users:"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="admin_panel")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_uptime":
        await query.answer()
        try:
            uptime_key = await get_setting("uptimerobot_api_key", "")
            if uptime_key:
                text = ("\ud83d\udd17 <b>UptimeRobot</b>\n\n"
                        f"API Key: <code>{uptime_key[:8]}...{uptime_key[-4:]}</code>\n"
                        "Status: \u2705 Connected")
            else:
                text = ("\ud83d\udd17 <b>UptimeRobot</b>\n\n"
                        "No API key set.\n"
                        "Set it in Settings \u2192 uptimerobot_api_key")
        except Exception as e:
            text = f"\ud83d\udd17 <b>UptimeRobot</b>\n\n\u26a0\ufe0f Error: {e}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("\ud83d\udd11 Set API Key", callback_data="sa_edit:uptimerobot_api_key")],
            [InlineKeyboardButton("\u00ab Back", callback_data="admin_panel")]
        ])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    from config import Config
    if user.id not in Config.SUPERADMIN_IDS:
        return False

    editing_key = context.user_data.get("admin_editing")
    if editing_key:
        new_value = update.message.text.strip()
        try:
            await set_setting(editing_key, new_value)
            await update.message.reply_text(
                f"\u2705 Setting updated!\n\n<code>{editing_key}</code> = {html_escape(new_value)}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Settings", callback_data="sa_settings")]])
            )
        except Exception as e:
            await update.message.reply_text(f"\u26a0\ufe0f Error: {e}")
        context.user_data.pop("admin_editing", None)
        return True

    action = context.user_data.get("admin_action")
    if not action:
        return False

    text = update.message.text.strip()

    if action == "ban":
        try:
            uid = int(text)
            await ban_user(uid)
            await update.message.reply_text(f"\ud83d\udeab User {uid} banned.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Users", callback_data="sa_users")]]))
        except ValueError:
            await update.message.reply_text("\u26a0\ufe0f Invalid user ID.")
        except Exception as e:
            await update.message.reply_text(f"\u26a0\ufe0f Error: {e}")
        context.user_data.pop("admin_action", None)
        return True

    elif action == "unban":
        try:
            uid = int(text)
            await unban_user(uid)
            await update.message.reply_text(f"\u2705 User {uid} unbanned.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Users", callback_data="sa_users")]]))
        except ValueError:
            await update.message.reply_text("\u26a0\ufe0f Invalid user ID.")
        except Exception as e:
            await update.message.reply_text(f"\u26a0\ufe0f Error: {e}")
        context.user_data.pop("admin_action", None)
        return True

    elif action == "set_tier":
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("\u26a0\ufe0f Format: <code>user_id tier</code>", parse_mode="HTML")
            return True
        try:
            uid = int(parts[0])
            tier = parts[1].lower()
            if tier not in ("free", "basic", "premium", "business"):
                await update.message.reply_text("\u26a0\ufe0f Valid tiers: free, basic, premium, business")
                return True
            await set_user_tier(uid, tier)
            await update.message.reply_text(f"\ud83c\udfc6 User {uid} tier set to {tier}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Users", callback_data="sa_users")]]))
        except ValueError:
            await update.message.reply_text("\u26a0\ufe0f Invalid user ID.")
        except Exception as e:
            await update.message.reply_text(f"\u26a0\ufe0f Error: {e}")
        context.user_data.pop("admin_action", None)
        return True

    elif action == "broadcast_all":
        context.user_data.pop("admin_action", None)
        try:
            import asyncio
            user_ids = await get_all_user_ids()
            status_msg = await update.message.reply_text(f"\ud83d\udce3 Broadcasting to {len(user_ids)} users...")
            sent = 0
            failed = 0
            for uid in user_ids:
                try:
                    await context.bot.send_message(uid, text, parse_mode="HTML")
                    sent += 1
                except Exception:
                    failed += 1
                if (sent + failed) % 50 == 0:
                    try:
                        await status_msg.edit_text(f"\ud83d\udce3 Broadcasting... {sent}/{len(user_ids)}")
                    except:
                        pass
                    await asyncio.sleep(1)
            await status_msg.edit_text(f"\ud83d\udce3 Broadcast complete!\n\u2705 Sent: {sent}\n\u274c Failed: {failed}")
        except Exception as e:
            await update.message.reply_text(f"\u26a0\ufe0f Error: {e}")
        return True

    return False
