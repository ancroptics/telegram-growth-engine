"""Handle chat join requests — core bot functionality."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import (
    get_managed_channel, log_join_request, approve_join_request_db,
    get_or_create_end_user, update_channel_stats, get_force_sub_channels
)
from utils.helpers import replace_variables
from services.language_service import get_welcome_for_language
from services.watermark_service import get_watermark

logger = logging.getLogger(__name__)


async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming chat join requests."""
    join_request = update.chat_join_request
    if not join_request:
        return

    user = join_request.from_user
    chat = join_request.chat
    chat_id = chat.id
    user_id = user.id

    logger.info(f"Join request from {user_id} for chat {chat_id} ({chat.title})")

    # Get channel config
    channel = await get_managed_channel(chat_id)
    if not channel:
        logger.warning(f"Join request for unmanaged channel {chat_id}")
        return

    # Log the request
    await log_join_request(user_id, chat_id, status="pending")
    await update_channel_stats(chat_id, requests=1)

    # Register end user
    await get_or_create_end_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
    )

    # Check force subscribe
    if channel.get("force_subscribe_enabled"):
        force_channels = await get_force_sub_channels(chat_id)
        if force_channels:
            # Check if user has joined all required channels
            all_joined = True
            missing_channels = []
            for fc in force_channels:
                try:
                    fc_id = fc if isinstance(fc, str) else fc.get("username", fc.get("chat_id"))
                    if isinstance(fc_id, str) and not fc_id.startswith("@"):
                        fc_id = f"@{fc_id}"
                    member = await context.bot.get_chat_member(fc_id, user_id)
                    if member.status in ("left", "kicked"):
                        all_joined = False
                        missing_channels.append(fc_id)
                except Exception as e:
                    logger.error(f"Error checking force sub {fc}: {e}")
                    pass

            if not all_joined:
                # Send DM with force subscribe buttons
                buttons = []
                for mc in missing_channels:
                    name = mc.lstrip("@")
                    buttons.append([InlineKeyboardButton(
                        f"\ud83d\udc49 Join @{name}",
                        url=f"https://t.me/{name}"
                    )])
                buttons.append([InlineKeyboardButton(
                    "\u2705 I've Joined All \u2014 Verify",
                    callback_data=f"fs_verify:{chat_id}"
                )])
                try:
                    await context.bot.send_message(
                        user_id,
                        f"\ud83d\udd12 <b>Join {chat.title}</b>\n\n"
                        f"To get approved, please join these channels first:\n",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(buttons),
                    )
                    await update_channel_stats(chat_id, dms_sent=1)
                except Exception as e:
                    logger.error(f"Failed to send force sub DM to {user_id}: {e}")
                return  # Don't auto-approve yet

    # Check drip mode
    if channel.get("drip_enabled"):
        logger.info(f"Drip mode active for {chat_id} \u2014 request queued")
        # Don't approve now, scheduler will handle it
        return

    # Auto approve
    if channel.get("auto_approve", True):
        try:
            await join_request.approve()
            await approve_join_request_db(user_id, chat_id, method="auto")
            await update_channel_stats(chat_id, approved=1)
            logger.info(f"Auto-approved {user_id} for {chat_id}")
        except Exception as e:
            logger.error(f"Failed to approve {user_id} for {chat_id}: {e}")
            return

    # Send welcome DM
    if channel.get("welcome_dm_enabled"):
        try:
            # Get welcome message (with i18n support)
            lang_code = user.language_code
            welcome_text = get_welcome_for_language(channel, lang_code)
            if not welcome_text:
                welcome_text = channel.get("welcome_message", "")

            if welcome_text:
                # Replace variables
                welcome_text = replace_variables(welcome_text, user=user, channel=channel)

                # Add watermark for free tier
                watermark = await get_watermark(channel, channel.get("owner_id", 0))
                welcome_text += watermark

                # Check for welcome media
                welcome_media_id = channel.get("welcome_media_file_id")
                welcome_media_type = channel.get("welcome_media_type")

                if welcome_media_id and welcome_media_type == "photo":
                    await context.bot.send_photo(
                        user_id,
                        welcome_media_id,
                        caption=welcome_text,
                        parse_mode="HTML",
                    )
                elif welcome_media_id and welcome_media_type == "video":
                    await context.bot.send_video(
                        user_id,
                        welcome_media_id,
                        caption=welcome_text,
                        parse_mode="HTML",
                    )
                else:
                    await context.bot.send_message(
                        user_id,
                        welcome_text,
                        parse_mode="HTML",
                    )

                await update_channel_stats(chat_id, dms_sent=1)
                logger.info(f"Welcome DM sent to {user_id} for {chat_id}")

        except Exception as e:
            if "blocked" in str(e).lower():
                logger.info(f"User {user_id} has blocked the bot")
            else:
                logger.error(f"Failed to send welcome DM to {user_id}: {e}")
