"""Auto poster handlers."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import get_auto_post_groups, create_auto_post_schedule

logger = logging.getLogger(__name__)

async def autopost_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups = await get_auto_post_groups(update.effective_user.id)
    if not groups:
        await update.message.reply_text("\u23f0 No groups connected. Add me as admin to a group first!")
        return
    text = "\u23f0 <b>Auto Poster</b>\nSelect a group:"
    buttons = [[InlineKeyboardButton(g.get("chat_title", "?")[:30], callback_data=f"ap_group:{g['chat_id']}")] for g in groups]
    buttons.append([InlineKeyboardButton("\u00ab Back", callback_data="main_menu")])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def autopost_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setup = context.user_data.get("autopost_setup")
    if not setup:
        return
    group_id = setup.get("group_id")
    interval = setup.get("interval", 60)
    content = update.message.text
    context.user_data.pop("autopost_setup", None)
    sid = await create_auto_post_schedule(update.effective_user.id, group_id, content, "text", interval)
    await update.message.reply_text(f"\u2705 Auto post scheduled (ID: {sid})! Posts every {interval} minutes.")

async def handle_auto_poster_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "auto_poster":
        groups = await get_auto_post_groups(update.effective_user.id)
        if not groups:
            await query.message.edit_text("\u23f0 No groups connected.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="main_menu")]]))
            return
        buttons = [[InlineKeyboardButton(g.get("chat_title", "?")[:30], callback_data=f"ap_group:{g['chat_id']}")] for g in groups]
        buttons.append([InlineKeyboardButton("\u00ab Back", callback_data="main_menu")])
        await query.message.edit_text("\u23f0 <b>Auto Poster</b>\nSelect a group:", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("ap_group:"):
        group_id = int(data.split(":")[1])
        context.user_data["autopost_setup"] = {"group_id": group_id, "interval": 60}
        await query.message.edit_text("\u23f0 Send the message content for auto-posting (will repeat every 60 min):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="auto_poster")]]))
