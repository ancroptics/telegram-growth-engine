"""Auth, rate limiting, and tracking decorators."""
import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from database.models import get_channel_owner, get_owner_tier, track_interaction
from utils.rate_limiter import rate_limiter
from utils.constants import TIER_LIMITS

logger = logging.getLogger(__name__)

def superadmin_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user.id not in Config.SUPERADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("\u26d4 Superadmin only.", show_alert=True)
            else:
                await update.message.reply_text("\u26d4 Superadmin only.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def channel_owner_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        owner = await get_channel_owner(user.id)
        if not owner:
            msg = "You don't have any channels. Add me as admin to a channel first!"
            if update.callback_query:
                await update.callback_query.answer(msg, show_alert=True)
            else:
                await update.message.reply_text(msg)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def rate_limited(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not rate_limiter.is_allowed(user.id):
            if update.callback_query:
                await update.callback_query.answer("\u23f3 Too fast! Wait a moment.", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def premium_required(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        tier = await get_owner_tier(user.id)
        if tier == "free":
            msg = "\ud83d\udc8e This feature requires Premium. Use /premium to upgrade!"
            if update.callback_query:
                await update.callback_query.answer(msg, show_alert=True)
            else:
                await update.message.reply_text(msg)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def track_action(action_name: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            try:
                await track_interaction(user.id, action_name)
            except Exception:
                pass
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
