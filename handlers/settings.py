"""Settings handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import get_owner

async def settings_callback(update, context):
    query = update.callback_query
    await query.answer()
    owner = await get_owner(query.from_user.id)
    tier = owner.get("tier", "free") if owner else "free"
    text = (f"Settings\n\nTier: {tier.upper()}\nUser ID: {query.from_user.id}\n"
            f"Username: @{query.from_user.username or 'N/A'}")
    buttons = [[InlineKeyboardButton("Premium", callback_data="premium_menu")],
               [InlineKeyboardButton("Back", callback_data="main_menu")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
