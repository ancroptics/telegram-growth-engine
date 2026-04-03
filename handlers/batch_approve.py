"""Batch approve/decline and drip management."""
from html import escape as html_escape
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest, RetryAfter
from database.models import (
    get_managed_channel, get_pending_requests, approve_join_request_db,
    decline_join_request_db, update_channel_setting
)
from utils.keyboards import back_kb
from utils.helpers import format_number

logger = logging.getLogger(__name__)


async def handle_batch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("batch_approve:"):
        chat_id = int(data.split(":")[1])
        await query.answer("Processing...")
        await _batch_approve(update, context, chat_id)

    elif data.startswith("batch_decline:"):
        chat_id = int(data.split(":")[1])
        await query.answer("Processing...")
        await _batch_decline(update, context, chat_id)

    elif data.startswith("drip_toggle:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel:
            await query.answer("Channel not found", show_alert=True)
            return
        new_val = not channel.get("drip_enabled", False)
        await update_channel_setting(chat_id, "drip_enabled", new_val)
        status = "enabled" if new_val else "disabled"
        await query.answer(f"Drip mode {status}!", show_alert=True)

    elif data.startswith("drip_speed:"):
        parts = data.split(":")
        chat_id = int(parts[1])
        speed = int(parts[2]) if len(parts) > 2 else 10
        await update_channel_setting(chat_id, "drip_speed", speed)
        await query.answer(f"Drip speed set to {speed}/batch", show_alert=True)

    elif data.startswith("pending_list:"):
        chat_id = int(data.split(":")[1])
        await _show_pending(update, context, chat_id)


async def _batch_approve(update, context, chat_id):
    query = update.callback_query
    pending = await get_pending_requests(chat_id, limit=200)

    if not pending:
        await query.message.edit_text(
            "\u2705 No pending requests!",
            reply_markup=back_kb(f"manage_ch:{chat_id}")
        )
        return

    approved = 0
    failed = 0
    total = len(pending)

    status_msg = await query.message.edit_text(
        f"\u23f3 Approving {total} users..."
    )

    for req in pending:
        user_id = req.get("user_id")
        try:
            await context.bot.approve_chat_join_request(chat_id, user_id)
            await approve_join_request_db(chat_id, user_id)
            approved += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await context.bot.approve_chat_join_request(chat_id, user_id)
                await approve_join_request_db(chat_id, user_id)
                approved += 1
            except:
                failed += 1
        except BadRequest:
            await approve_join_request_db(chat_id, user_id)
            approved += 1
        except Exception as e:
            logger.error(f"Batch approve error for {user_id}: {e}")
            failed += 1

        if approved % 25 == 0 and approved > 0:
            try:
                await status_msg.edit_text(f"\u23f3 Approved {approved}/{total}...")
            except:
                pass
            await asyncio.sleep(0.5)

    from database.models import update_channel_stats
    await update_channel_stats(chat_id, total_approved=approved)

    await query.message.edit_text(
        f"\u2705 Batch approve complete!\n\n"
        f"\u2705 Approved: {approved}\n"
        f"\u274c Failed: {failed}",
        reply_markup=back_kb(f"manage_ch:{chat_id}")
    )


async def _batch_decline(update, context, chat_id):
    query = update.callback_query
    pending = await get_pending_requests(chat_id, limit=200)

    if not pending:
        await query.message.edit_text(
            "\u2705 No pending requests!",
            reply_markup=back_kb(f"manage_ch:{chat_id}")
        )
        return

    declined = 0
    failed = 0

    for req in pending:
        user_id = req.get("user_id")
        try:
            await context.bot.decline_chat_join_request(chat_id, user_id)
            await decline_join_request_db(chat_id, user_id)
            declined += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await context.bot.decline_chat_join_request(chat_id, user_id)
                await decline_join_request_db(chat_id, user_id)
                declined += 1
            except:
                failed += 1
        except Exception:
            failed += 1

        if declined % 25 == 0 and declined > 0:
            await asyncio.sleep(0.5)

    await query.message.edit_text(
        f"\u274c Batch decline complete!\n\n"
        f"Declined: {declined}\n"
        f"Failed: {failed}",
        reply_markup=back_kb(f"manage_ch:{chat_id}")
    )


async def _show_pending(update, context, chat_id):
    query = update.callback_query
    await query.answer()
    pending = await get_pending_requests(chat_id, limit=20)

    if not pending:
        text = "\u2705 No pending requests!"
    else:
        text = f"\u23f3 <b>Pending Requests</b> ({len(pending)}+):\n\n"
        for req in pending[:20]:
            uid = req.get("user_id", "?")
            uname = req.get("username") or req.get("first_name") or "?"
            text += f"\u2022 {html_escape(str(uname))} (<code>{uid}</code>)\n"

    await query.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=back_kb(f"manage_ch:{chat_id}")
    )
