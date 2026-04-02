"""Join request handler — core auto-approve + welcome DM."""
import logging
import asyncio
from telegram import Update, ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import Forbidden, BadRequest, RetryAfter
from database.models import (
    get_managed_channel, approve_join_request_db, record_join_request,
    ensure_user, update_channel_stats, get_owner_channels,
    increment_dm_count
)
from utils.helpers import replace_variables
from config import Config
import json as _json

logger = logging.getLogger(__name__)

async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request: ChatJoinRequest = update.chat_join_request
    if not request: return
    user = request.from_user
    chat = request.chat
    logger.info(f"Join request: user={user.id} chat={chat.id} ({chat.title})")
    channel = await get_managed_channel(chat.id)
    if not channel:
        logger.warning(f"Unmanaged channel {chat.id}")
        return
    await ensure_user(user.id, user.username, user.full_name)
    await record_join_request(user.id, chat.id, user.full_name, user.username)
    # Check force subscribe
    if channel.get("force_subscribe_enabled"):
        force_channels = channel.get("force_subscribe_channels") or []
        if isinstance(force_channels, str):
            force_channels = _json.loads(force_channels)
        if force_channels:
            await send_force_sub_message(context, user, chat, force_channels)
            return
    # Auto-approve or drip
    if channel.get("drip_enabled"):
        logger.info(f"Drip mode for {chat.id}, request queued")
        return
    if channel.get("auto_approve", True):
        try:
            await request.approve()
            await approve_join_request_db(user.id, chat.id, "auto")
            await update_channel_stats(chat.id, approved=1)
            logger.info(f"Auto-approved {user.id} for {chat.id}")
        except RetryAfter as e:
            logger.warning(f"Rate limited, retry after {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            try:
                await request.approve()
                await approve_join_request_db(user.id, chat.id, "auto")
                await update_channel_stats(chat.id, approved=1)
            except Exception as e2:
                logger.error(f"Retry approve failed: {e2}")
        except BadRequest as e:
            logger.error(f"Approve failed: {e}")
            return
        except Exception as e:
            logger.error(f"Approve error: {e}")
            return
        # Send welcome DM
        if channel.get("welcome_dm_enabled", True):
            await send_welcome_dm(context, user, channel)

async def send_welcome_dm(context: ContextTypes.DEFAULT_TYPE, user, channel: dict):
    welcome_text = channel.get("welcome_message") or (
        f"\ud83c\udf89 Welcome to <b>{channel.get('chat_title','our channel')}</b>!\n\n"
        f"Hello {user.first_name}! Thanks for joining.\n\n"
        f"\ud83d\udc49 Stay active and invite friends!"
    )
    welcome_text = replace_variables(welcome_text, user=user, channel=channel)
    extra = {}
    ref_link = f"https://t.me/{Config.BOT_USERNAME}?start={user.id}"
    welcome_text = welcome_text.replace("{referral_link}", ref_link)
    media_type = channel.get("welcome_media_type")
    media_fid = channel.get("welcome_media_file_id")
    try:
        if media_type == "photo" and media_fid:
            await context.bot.send_photo(user.id, media_fid, caption=welcome_text, parse_mode="HTML")
        elif media_type == "video" and media_fid:
            await context.bot.send_video(user.id, media_fid, caption=welcome_text, parse_mode="HTML")
        else:
            # Add referral button
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udc65 Invite Friends", url=ref_link)]])
            await context.bot.send_message(user.id, welcome_text, parse_mode="HTML", reply_markup=kb)
        await increment_dm_count(channel["chat_id"])
        logger.info(f"Welcome DM sent to {user.id}")
    except Forbidden:
        logger.info(f"User {user.id} blocked bot")
    except Exception as e:
        logger.error(f"DM failed to {user.id}: {e}")

async def send_force_sub_message(context: ContextTypes.DEFAULT_TYPE, user, chat, force_channels: list):
    text = (f"\ud83d\udd12 <b>Join Required Channels</b>\n\n"
            f"To join <b>{chat.title}</b>, first join these channels:\n\n")
    buttons = []
    for fc in force_channels:
        username = fc.get("username", "")
        title = fc.get("title", "Channel")
        if username:
            buttons.append([InlineKeyboardButton(f"\ud83d\udce2 {title}", url=f"https://t.me/{username}")])
            text += f"  \u2022 @{username}\n"
    buttons.append([InlineKeyboardButton("\u2705 I've Joined — Verify", callback_data=f"fs_verify:{chat.id}")])
    try:
        await context.bot.send_message(user.id, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Forbidden:
        logger.info(f"Can't send force-sub msg to {user.id}")
    except Exception as e:
        logger.error(f"Force-sub msg error: {e}")
