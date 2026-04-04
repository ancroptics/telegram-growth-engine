"""Join request handler."""
import logging, asyncio
from telegram import Update
from telegram.ext import ContextTypes
from database.models import (get_managed_channel, get_or_create_end_user, log_join_request,
    approve_join_request_db, update_join_request_dm, increment_channel_stat, update_daily_stats)
logger = logging.getLogger(__name__)

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jr = update.chat_join_request
    if not jr: return
    user = jr.from_user
    chat = jr.chat
    ch = await get_managed_channel(chat.id)
    if not ch or not ch.get("is_active"): return
    await get_or_create_end_user(user.id, user.username, user.first_name, user.last_name,
                                  getattr(user, "language_code", None), "join_request", chat.id)
    await log_join_request(user.id, chat.id, user.username, user.first_name, getattr(user, "language_code", None))
    await update_daily_stats(chat.id, joins=1)
    if not ch.get("auto_approve"): return
    mode = ch.get("approve_mode", "instant")
    if mode == "manual": return
    if mode == "drip":
        await asyncio.sleep(30)
    try:
        await jr.approve()
        await approve_join_request_db(user.id, chat.id, method=mode)
        await increment_channel_stat(chat.id, total_approved=1)
        await update_daily_stats(chat.id, approvals=1)
        logger.info(f"Approved {user.id} for {chat.title}")
    except Exception as e:
        logger.error(f"Approve error: {e}")
        return
    if not ch.get("welcome_dm_enabled"): return
    msg = ch.get("welcome_message", "Welcome!")
    msg = msg.replace("{user_name}", user.first_name or "").replace("{channel_name}", chat.title or "").replace("{user_id}", str(user.id))
    try:
        sent = await context.bot.send_message(user.id, msg)
        await update_join_request_dm(user.id, chat.id, True, sent.message_id)
        await increment_channel_stat(chat.id, total_dm_sent=1)
        await update_daily_stats(chat.id, dms_sent=1)
    except Exception as e:
        reason = str(e)[:100]
        await update_join_request_dm(user.id, chat.id, False, reason=reason)
        await increment_channel_stat(chat.id, total_dm_failed=1)
        await update_daily_stats(chat.id, dms_failed=1)
