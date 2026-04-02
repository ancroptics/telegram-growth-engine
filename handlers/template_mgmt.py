"""Template management."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_templates, save_template, delete_template
from utils.keyboards import back_kb

logger = logging.getLogger(__name__)

async def handle_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    templates = await get_templates(update.effective_user.id)
    if not templates:
        text = "📝 <b>Templates</b>\n\nNo templates yet. Send /newtemplate <name> to create one."
    else:
        text = "📝 <b>Your Templates</b>\n\n"
        for t in templates:
            text += f"• <b>{t['name']}</b> ({t['content_type']}) — used {t.get('use_count', 0)}x\n"
    await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb())

async def new_template_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /newtemplate <name>")
        return
    context.user_data["creating_template"] = context.args[0]
    await update.message.reply_text(f"📝 Send content for '{context.args[0]}'. /cancel to abort")

async def del_template_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /deltemplate <name>")
        return
    await delete_template(update.effective_user.id, context.args[0])
    await update.message.reply_text(f"✅ Template '{context.args[0]}' deleted.")

async def template_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("creating_template")
    if not name: return False
    message = update.message
    if message.text and message.text.startswith("/cancel"):
        del context.user_data["creating_template"]
        await message.reply_text("❌ Cancelled.")
        return True
    if message.photo:
        await save_template(update.effective_user.id, name, "photo", media_file_id=message.photo[-1].file_id, caption=message.caption)
    elif message.video:
        await save_template(update.effective_user.id, name, "video", media_file_id=message.video.file_id, caption=message.caption)
    elif message.text:
        await save_template(update.effective_user.id, name, "text", content=message.text)
    else:
        await message.reply_text("Unsupported type.")
        return True
    del context.user_data["creating_template"]
    await message.reply_text(f"✅ Template '{name}' saved!")
    return True
