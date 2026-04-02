"""Auto-poster management."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_auto_post_groups, create_auto_post_schedule
from utils.keyboards import back_kb
from utils.decorators import channel_owner_only

logger = logging.getLogger(__name__)

async def handle_auto_poster_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user
    await query.answer()

    if data == "auto_poster":
        groups = await get_auto_post_groups(user.id)
        if not groups:
            text = (
                "🤖 <b>Auto Poster</b>\n\n"
                "No groups connected.\n\n"
                "Add me to a group as admin, and it will appear here.\n"
                "Then you can set up recurring posts!"
            )
        else:
            text = "🤖 <b>Auto Poster — Groups</b>\n\n"
            for g in groups:
                text += f"• {g.get('chat_title', '?')} (ID: {g['chat_id']})\n"
            text += "\nUse /autopost <group_id> <interval_min> to create a schedule.\nThen send the content."
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb())

async def autopost_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /autopost <group_chat_id> <interval_minutes>")
        return
    try:
        group_id = int(args[0])
        interval = int(args[1])
        context.user_data["autopost_setup"] = {"group_id": group_id, "interval": interval}
        await update.message.reply_text(f"📝 Send the content to auto-post every {interval} minutes.\n/cancel to abort")
    except ValueError:
        await update.message.reply_text("Invalid arguments.")

async def autopost_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setup = context.user_data.get("autopost_setup")
    if not setup: return False
    message = update.message
    if message.text and message.text.startswith("/cancel"):
        del context.user_data["autopost_setup"]
        await message.reply_text("❌ Cancelled.")
        return True
    content = message.text or message.caption or ""
    sid = await create_auto_post_schedule(update.effective_user.id, setup["group_id"], content, "text", setup["interval"])
    del context.user_data["autopost_setup"]
    await message.reply_text(f"✅ Auto-post schedule created! ID: {sid}\nInterval: {setup['interval']} min")
    return True
