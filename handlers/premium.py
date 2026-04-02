"""Premium subscription management."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from database.models import get_owner_tier
from utils.keyboards import premium_upgrade_kb, back_kb
from utils.constants import TIER_EMOJI

logger = logging.getLogger(__name__)

async def handle_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user
    await query.answer()
    if data == "premium_info":
        tier = await get_owner_tier(user.id)
        text = (f"💎 <b>Premium Plans</b>\nYour Plan: {TIER_EMOJI.get(tier,'')} {tier.title()}\n\n"
                f"🆓 FREE: 1 channel, auto-approve, basic DM\n"
                f"💎 PREMIUM ₹{Config.PREMIUM_PRICE_MONTHLY}/mo: 5 channels, clone bot, media DM, force sub, drip\n"
                f"💼 BUSINESS ₹{Config.BUSINESS_PRICE_MONTHLY}/mo: Unlimited, 5 clones, auto-poster, priority support")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=premium_upgrade_kb())
    elif data.startswith("premium_buy:"):
        tier = data.split(":")[1]
        await query.message.edit_text(f"💳 Contact admin to upgrade to {tier.title()}.", parse_mode="HTML", reply_markup=back_kb("premium_info"))
