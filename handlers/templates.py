"""Templates handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import get_templates, get_template, save_template, delete_template

async def templates_menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    tpls = await get_templates(query.from_user.id)
    buttons = [[InlineKeyboardButton(t.get("name","?"), callback_data=f"view_tpl:{t.get('name','')}")] for t in tpls]
    buttons.append([InlineKeyboardButton("Create Template", callback_data="create_tpl")])
    buttons.append([InlineKeyboardButton("Back", callback_data="main_menu")])
    await query.message.edit_text(f"Templates ({len(tpls)}):", reply_markup=InlineKeyboardMarkup(buttons))

async def create_tpl_callback(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_template"] = True
    await query.message.edit_text("Send template in format:\nname | type | content\n\nTypes: welcome, broadcast, custom",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="templates_menu")]]))

async def handle_template_input(update, context):
    if not context.user_data.get("awaiting_template"): return False
    context.user_data.pop("awaiting_template", None)
    parts = update.message.text.split("|", 2)
    if len(parts) < 3:
        await update.message.reply_text("Format: name | type | content"); return True
    name, tpl_type, content = [p.strip() for p in parts]
    await save_template(update.effective_user.id, name, tpl_type, content)
    await update.message.reply_text(f"Template '{name}' saved!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Templates", callback_data="templates_menu")]]))
    return True

async def view_tpl_callback(update, context):
    query = update.callback_query
    await query.answer()
    name = query.data.split(":", 1)[1]
    tpl = await get_template(query.from_user.id, name)
    if not tpl:
        await query.message.edit_text("Template not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="templates_menu")]]))
        return
    text = f"Template: {name}\nType: {tpl.get('type','')}\n\n{tpl.get('content','')}"
    buttons = [[InlineKeyboardButton("Delete", callback_data=f"del_tpl:{name}")],
               [InlineKeyboardButton("Back", callback_data="templates_menu")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def del_tpl_callback(update, context):
    query = update.callback_query
    name = query.data.split(":", 1)[1]
    await delete_template(query.from_user.id, name)
    await query.answer(f"Deleted '{name}'", show_alert=True)
    query.data = "templates_menu"
    await templates_menu_callback(update, context)
