"""Bot cloning (multi-bot)."""
import logging
from telegram import Update, Bot
from telegram.ext import ContextTypes
from database.models import get_cloned_bots, create_clone_bot, delete_clone_bot, get_owner_tier
from utils.keyboards import clone_kb, back_kb
from utils.constants import TIER_LIMITS

logger = logging.getLogger(__name__)

async def handle_clone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user
    await query.answer()

    if data == "clone_list":
        tier = await get_owner_tier(user.id)
        max_clones = TIER_LIMITS.get(tier, {}).get("max_clones", 0)
        clones = await get_cloned_bots(user.id)
        text = (f"\U0001f916 <b>Bot Clones</b>\n\n"
                f"Tier: {tier.capitalize()} (max {max_clones} clones)\n"
                f"Active: {len(clones)}/{max_clones}\n\n")
        if clones:
            for c in clones:
                status = '\u2705' if c.get('is_active') else '\u274c'
                text += f"  {status} @{c.get('bot_username','?')}\n"
        else:
            text += "No clones yet.\n"
        text += "\nTo create a clone:\n1. Create a bot via @BotFather\n2. Send /clone {bot_token}"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=clone_kb())

    elif data == "clone_add":
        context.user_data["adding_clone"] = True
        await query.message.edit_text("\U0001f916 Send the bot token from @BotFather.\n/cancel to abort", parse_mode="HTML")

    elif data.startswith("clone_delete:"):
        clone_id = int(data.split(":")[1])
        await delete_clone_bot(clone_id, user.id)
        await query.answer("\u2705 Clone deleted", show_alert=True)
        update.callback_query.data = "clone_list"
        await handle_clone_callback(update, context)

async def clone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /clone {bot_token}")
        return
    token = context.args[0].strip()
    tier = await get_owner_tier(user.id)
    max_clones = TIER_LIMITS.get(tier, {}).get("max_clones", 0)
    if max_clones <= 0:
        await update.message.reply_text("\U0001f48e Cloning requires Premium. Use /premium")
        return
    clones = await get_cloned_bots(user.id)
    if len(clones) >= max_clones:
        await update.message.reply_text(f"\u274c Clone limit reached ({max_clones}).")
        return
    # Validate token using httpx directly (avoids PTB Bot initialization issues)
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise ValueError("Invalid token")
            bot_info = data["result"]
            bot_username = bot_info.get("username", "unknown")
            bot_name = bot_info.get("first_name", "Clone Bot")
    except Exception as e:
        logger.error(f"Clone token validation failed: {e}")
        await update.message.reply_text("\u274c Invalid bot token. Make sure you copied it correctly from @BotFather.")
        return
    clone_id = await create_clone_bot(user.id, token, bot_username, bot_name)
    await update.message.reply_text(
        f"\u2705 Clone created!\n\n"
        f"Bot: @{bot_username}\n"
        f"Clone ID: {clone_id}\n\n"
        f"Note: The clone bot mirrors your channel settings. "
        f"Add it as admin to your channels to use it."
    )

async def clone_token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("adding_clone"): return False
    message = update.message
    if message.text and message.text.startswith("/cancel"):
        del context.user_data["adding_clone"]
        await message.reply_text("\u274c Cancelled.")
        return True
    if message.text:
        context.args = [message.text.strip()]
        del context.user_data["adding_clone"]
        await clone_command(update, context)
        return True
    return False
