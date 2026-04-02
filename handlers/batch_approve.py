"""Batch approve/decline and drip management."""
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest, RetryAfter
from database.models import (
    get_managed_channel, get_pending_requests, approve_join_request_db,
    decline_join_request_db, update_channel_setting
)
from utils.keyboards import batch_kb, drip_kb, back_kb
from utils.helpers import format_number

logger = logging.getLogger(__name__)

async def handle_batch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user

    if data.startswith("ch_pending:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        await query.answer()
        pending = await get_pending_requests(chat_id, limit=100)
        text = (f"\ud83d\udccb <b>Pending Requests</b>\n\n"
                f"\ud83d\udce2 {channel.get('chat_title','')}\n"
                f"\u23f3 Pending: {len(pending)}\n\n")
        if pending:
            text += "Recent requests:\n"
            for r in pending[:10]:
                text += f"  \u2022 {r.get('user_full_name','?')} (ID: {r['user_id']})\n"
            if len(pending) > 10:
                text += f"  ... +{len(pending)-10} more\n"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=batch_kb(chat_id))

    elif data.startswith("batch_approve:"):
        chat_id = int(data.split(":")[1])
        await query.answer("\u23f3 Approving...")
        pending = await get_pending_requests(chat_id, limit=200)
        approved = 0
        for req in pending:
            try:
                await context.bot.approve_chat_join_request(chat_id, req["user_id"])
                await approve_join_request_db(req["user_id"], chat_id, "batch")
                approved += 1
            except BadRequest: await approve_join_request_db(req["user_id"], chat_id, "batch")
            except RetryAfter as e: await asyncio.sleep(e.retry_after)
            except Exception as e: logger.error(f"Approve error: {e}")
            await asyncio.sleep(0.3)
        await query.message.edit_text(f"\u2705 Batch approved {approved} users!", reply_markup=back_kb(f"manage_ch:{chat_id}"))

    elif data.startswith("batch_decline:"):
        chat_id = int(data.split(":")[1])
        await query.answer("\u23f3 Declining...")
        pending = await get_pending_requests(chat_id, limit=200)
        declined = 0
        for req in pending:
            try:
                await context.bot.decline_chat_join_request(chat_id, req["user_id"])
                await decline_join_request_db(req["user_id"], chat_id)
                declined += 1
            except Exception: pass
            await asyncio.sleep(0.3)
        await query.message.edit_text(f"\u274c Batch declined {declined} users.", reply_markup=back_kb(f"manage_ch:{chat_id}"))

    elif data.startswith("drip_config:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        await query.answer()
        rate = channel.get("drip_rate", 50)
        start_h = channel.get("drip_active_start", 8)
        end_h = channel.get("drip_active_end", 23)
        text = (f"\ud83d\udca7 <b>Drip Approve Config</b>\n\n"
                f"Rate: {rate} users per 5 min\n"
                f"Active: {start_h}:00 - {end_h}:00\n\n"
                f"Use /setdrip {chat_id} <rate> <start_hour> <end_hour>")
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=drip_kb(chat_id))

    elif data.startswith("drip_start:"):
        chat_id = int(data.split(":")[1])
        await update_channel_setting(chat_id, drip_enabled=True)
        await query.answer("\ud83d\udca7 Drip approve enabled!", show_alert=True)
        update.callback_query.data = f"drip_config:{chat_id}"
        await handle_batch_callback(update, context)
