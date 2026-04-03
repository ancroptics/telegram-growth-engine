from html import escape as html_escape
"""Superadmin panel with full settings management."""
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
        [InlineKeyboardButton("📊 Platform Stats", callback_data="sa_stats"),
         InlineKeyboardButton("👥 Users", callback_data="sa_users")],
        [InlineKeyboardButton("📢 All Channels", callback_data="sa_channels"),
         InlineKeyboardButton("⚙️ Settings", callback_data="sa_settings")],
        [InlineKeyboardButton("📣 Broadcast All", callback_data="sa_broadcast")],
        [InlineKeyboardButton("🔗 UptimeRobot", callback_data="sa_uptime")],
        [InlineKeyboardButton("« Back", callback_data="main_menu")]
    ])


@superadmin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command."""
    await update.message.reply_text(
        "🔐 <b>Superadmin Panel</b>\n\nSelect an option:",
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all admin panel callbacks."""
    query = update.callback_query
    data = query.data
    user = update.effective_user

    from config import Config
    if user.id not in Config.SUPERADMIN_IDS:
        await query.answer("⛔ Not authorized", show_alert=True)
        return

    if data in ("admin_panel", "superadmin"):
        await query.message.edit_text(
            "🔐 <b>Superadmin Panel</b>\n\nSelect an option:",
            parse_mode="HTML",
            reply_markup=admin_panel_kb()
        )

    elif data == "sa_stats":
        try:
            stats = await get_global_stats()
            text = ("📊 <b>Platform Statistics</b>\n\n"
                    f"👥 Total Users: {format_number(stats.get('total_users', 0))}\n"
                    f"📢 Active Channels: {stats.get('active_channels', 0)}\n"
                    f"👤 Channel Owners: {stats.get('total_owners', 0)}\n\n"
                    f"<b>Today:</b>\n"
                    f"📥 Requests: {stats.get('today_requests', 0)}\n"
                    f"✅ Approved: {stats.get('today_approved', 0)}\n"
                    f"📨 DMs Sent: {stats.get('today_dms', 0)}")
        except Exception as e:
            text = f"📊 <b>Stats</b>\n\n⚠️ Error loading stats: {e}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="admin_panel")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_users":
        try:
            owners = await get_all_owners()
            text = "👥 <b>Channel Owners</b>\n\n"
            if not owners:
                text += "No owners yet."
            else:
                for o in owners[:20]:
                    uid = o.get("user_id", "?")
                    tier = o.get("tier", "free")
                    banned = "🚫" if o.get("is_banned") else ""
                    text += f"• <code>{uid}</code> [{tier}] {banned}\n"
                if len(owners) > 20:
                    text += f"\n... and {len(owners) - 20} more"
        except Exception as e:
            text = f"👥 <b>Users</b>\n\n⚠️ Error: {e}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Ban User", callback_data="sa_ban"),
             InlineKeyboardButton("✅ Unban User", callback_data="sa_unban")],
            [InlineKeyboardButton("🏆 Set Tier", callback_data="sa_set_tier")],
            [InlineKeyboardButton("« Back", callback_data="admin_panel")]
        ])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_channels":
        try:
            from database.models import get_all_active_channels
            channels = await get_all_active_channels()
            text = "📢 <b>All Active Channels</b>\n\n"
            if not channels:
                text += "No active channels."
            else:
                for ch in channels[:20]:
                    title = html_escape(ch.get("chat_title", "?"))
                    cid = ch.get("chat_id", "?")
                    owner = ch.get("owner_id", "?")
                    approved = ch.get("total_approved", 0)
                    text += f"• {title}\n  ID: <code>{cid}</code> | Owner: <code>{owner}</code> | ✅ {approved}\n"
                if len(channels) > 20:
                    text += f"\n... and {len(channels) - 20} more"
        except Exception as e:
            text = f"📢 <b>Channels</b>\n\n⚠️ Error: {e}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="admin_panel")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_settings":
        try:
            settings = await get_all_settings()
            text = "⚙️ <b>Platform Settings</b>\n\n"
            if not settings:
                text += "No settings configured yet.\n\nDefault settings will be used."
            else:
                for k, v in settings.items():
                    display_v = v if len(str(v)) < 50 else str(v)[:47] + "..."
                    text += f"• <code>{k}</code> = {html_escape(str(display_v))}\n"
            text += "\n\nTap a setting to edit:"
        except Exception as e:
            text = f"⚙️ <b>Settings</b>\n\n⚠️ Error: {e}"
            settings = {}
        kb = []
        editable = [
            ("support_username", "💬 Support Username"),
            ("welcome_text", "👋 Default Welcome"),
            ("maintenance_mode", "🔧 Maintenance Mode"),
            ("max_channels_free", "📢 Max Channels (Free)"),
            ("max_channels_premium", "📢 Max Channels (Premium)"),
        ]
        for key, label in editable:
            kb.append([InlineKeyboardButton(label, callback_data=f"sa_edit:{key}")])
        kb.append([InlineKeyboardButton("« Back", callback_data="admin_panel")])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("sa_edit:"):
        key = data.split(":", 1)[1]
        try:
            current = await get_setting(key, "(not set)")
        except:
            current = "(not set)"
        context.user_data["admin_editing"] = key
        text = (f"✏️ <b>Edit Setting</b>\n\n"
                f"Key: <code>{key}</code>\n"
                f"Current: {html_escape(str(current))}\n\n"
                f"Send the new value:")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sa_settings")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_ban":
        context.user_data["admin_action"] = "ban"
        text = "🚫 <b>Ban User</b>\n\nSend the user ID to ban:"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sa_users")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_unban":
        context.user_data["admin_action"] = "unban"
        text = "✅ <b>Unban User</b>\n\nSend the user ID to unban:"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sa_users")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_set_tier":
        context.user_data["admin_action"] = "set_tier"
        text = "🏆 <b>Set User Tier</b>\n\nSend: <code>user_id tier_name</code>\nExample: <code>123456 premium</code>"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sa_users")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_broadcast":
        context.user_data["admin_action"] = "broadcast_all"
        text = "📣 <b>Broadcast to All Users</b>\n\nSend the message to broadcast to all bot users:"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "sa_uptime":
        try:
            uptime_key = await get_setting("uptimerobot_api_key", "")
            if uptime_key:
                text = ("🔗 <b>UptimeRobot</b>\n\n"
                        f"API Key: <code>{uptime_key[:8]}...{uptime_key[-4:]}</code>\n"
                        "Status: ✅ Connected")
            else:
                text = ("🔗 <b>UptimeRobot</b>\n\n"
                        "No API key set.\n"
                        "Set it in Settings → uptimerobot_api_key")
        except Exception as e:
            text = f"🔗 <b>UptimeRobot</b>\n\n⚠️ Error: {e}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Set API Key", callback_data="sa_edit:uptimerobot_api_key")],
            [InlineKeyboardButton("« Back", callback_data="admin_panel")]
        ])
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle text input for admin actions. Returns True if handled."""
    user = update.effective_user
    from config import Config
    if user.id not in Config.SUPERADMIN_IDS:
        return False

    # Check if editing a setting
    editing_key = context.user_data.get("admin_editing")
    if editing_key:
        new_value = update.message.text.strip()
        try:
            await set_setting(editing_key, new_value)
            await update.message.reply_text(
                f"✅ Setting updated!\n\n<code>{editing_key}</code> = {html_escape(new_value)}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Settings", callback_data="sa_settings")]])
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
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
            await update.message.reply_text(f"🚫 User {uid} banned.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Users", callback_data="sa_users")]]))
        except ValueError:
            await update.message.reply_text("⚠️ Invalid user ID.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
        context.user_data.pop("admin_action", None)
        return True

    elif action == "unban":
        try:
            uid = int(text)
            await unban_user(uid)
            await update.message.reply_text(f"✅ User {uid} unbanned.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Users", callback_data="sa_users")]]))
        except ValueError:
            await update.message.reply_text("⚠️ Invalid user ID.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
        context.user_data.pop("admin_action", None)
        return True

    elif action == "set_tier":
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("⚠️ Format: <code>user_id tier</code>", parse_mode="HTML")
            return True
        try:
            uid = int(parts[0])
            tier = parts[1].lower()
            if tier not in ("free", "basic", "premium", "enterprise"):
                await update.message.reply_text("⚠️ Valid tiers: free, basic, premium, enterprise")
                return True
            await set_user_tier(uid, tier)
            await update.message.reply_text(f"🏆 User {uid} tier set to {tier}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Users", callback_data="sa_users")]]))
        except ValueError:
            await update.message.reply_text("⚠️ Invalid user ID.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
        context.user_data.pop("admin_action", None)
        return True

    elif action == "broadcast_all":
        context.user_data.pop("admin_action", None)
        try:
            user_ids = await get_all_user_ids()
            status_msg = await update.message.reply_text(f"📣 Broadcasting to {len(user_ids)} users...")
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
                        await status_msg.edit_text(f"📣 Broadcasting... {sent}/{len(user_ids)}")
                    except:
                        pass
            await status_msg.edit_text(f"📣 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
        return True

    return False
