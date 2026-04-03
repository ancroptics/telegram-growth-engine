"""Template management handlers."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import get_templates, save_template, delete_template

logger = logging.getLogger(__name__)


async def new_template_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /newtemplate <name>\nThen send the content.")
        return
    name = args[0]
    context.user_data["creating_template"] = name
    await update.message.reply_text(f"\ud83d\udccb Creating template \"{name}\". Send the content now (text, photo, or video):")


async def del_template_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /deltemplate <name>")
        return
    await delete_template(update.effective_user.id, args[0])
    await update.message.reply_text(f"\u2705 Template \"{args[0]}\" deleted.")


async def template_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.pop("creating_template", None)
    if not name:
        return
    msg = update.message
    if msg.photo:
        await save_template(msg.from_user.id, name, "photo", media_file_id=msg.photo[-1].file_id, caption=msg.caption)
    elif msg.video:
        await save_template(msg.from_user.id, name, "video", media_file_id=msg.video.file_id, caption=msg.caption)
    elif msg.document:
        await save_template(msg.from_user.id, name, "document", media_file_id=msg.document.file_id, caption=msg.caption)
    else:
        await save_template(msg.from_user.id, name, "text", content=msg.text)
    await msg.reply_text(f"\u2705 Template \"{name}\" saved!")


async def handle_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    if data in ("template_settings", "templates_list"):
        templates = await get_templates(user_id)
        if not templates:
            await query.message.edit_text("\ud83d\udccb No templates yet. Use /newtemplate <name> to create one.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="main_menu")]]))
            return
        text = "\ud83d\udccb <b>Your Templates</b>\n\n"
        for t in templates:
            text += f"\u2022 <b>{t.get('name', '?')}</b> ({t.get('content_type', '?')})\n"
        await query.message.edit_text(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u00ab Back", callback_data="main_menu")]]))
