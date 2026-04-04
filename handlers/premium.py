"""Premium handler."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import get_owner
from config import BOT_USERNAME
logger = logging.getLogger(__name__)

TIERS = {"free": {"channels": 2, "broadcasts": 10}, "pro": {"channels": 10, "broadcasts": 100, "price": "$9.99/mo"},
         "business": {"channels": 50, "broadcasts": 1000, "price": "$29.99/mo"}}

async def premium_menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    owner = await get_owner(query.from_user.id)
    tier = owner.get("tier", "free") if owner else "free"
    text = f"Current plan: {tier.upper()}\n\nUpgrade for more channels and broadcasts!"
    buttons = []
    if tier == "free":
        buttons.append([InlineKeyboardButton("Upgrade to Pro - $9.99/mo", callback_data="upgrade_pro")])
    if tier in ("free", "pro"):
        buttons.append([InlineKeyboardButton("Upgrade to Business - $29.99/mo", callback_data="upgrade_business")])
    buttons.append([InlineKeyboardButton("Referral Program", callback_data="referral_menu")])
    buttons.append([InlineKeyboardButton("Back", callback_data="main_menu")])
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def upgrade_callback(update, context):
    query = update.callback_query
    tier = query.data.replace("upgrade_", "")
    await query.answer(f"Contact @admin for {tier} upgrade. Payment integration coming soon!", show_alert=True)

async def referral_menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    owner = await get_owner(query.from_user.id)
    code = owner.get("referral_code", f"ref_{query.from_user.id}") if owner else f"ref_{query.from_user.id}"
    refs = owner.get("total_referrals", 0) if owner else 0
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    text = f"Referral Program\n\nYour link: {link}\nTotal referrals: {refs}\n\nShare to earn rewards!"
    await query.message.edit_text(text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="premium_menu")]]))
