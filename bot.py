"""Main bot entry point."""
import logging
import asyncio
from telegram import Update, ChatJoinRequest
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ChatJoinRequestHandler, filters
)
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def post_init(app):
    """Initialize services after bot starts."""
    from services.health_server import start_health_server
    await start_health_server()
    from services.scheduler import start_scheduler
    start_scheduler(app)
    me = await app.bot.get_me()
    logger.info(f"Bot started: @{me.username}")


async def handle_join_request(update: Update, context):
    """Handle channel join requests."""
    from handlers.batch_approve import process_join_request
    await process_join_request(update, context)


async def handle_text_message(update: Update, context):
    """Route text messages to appropriate handlers."""
    if not update.message or not update.message.text:
        return
    # Try each handler that expects text input
    from handlers.welcome_dm import welcome_message_handler
    if await welcome_message_handler(update, context):
        return
    from handlers.broadcast import broadcast_message_handler
    if await broadcast_message_handler(update, context):
        return
    from handlers.template_mgmt import template_content_handler
    if await template_content_handler(update, context):
        return
    from handlers.clone_bot import clone_token_handler
    if await clone_token_handler(update, context):
        return
    from handlers.auto_poster import autopost_content_handler
    if await autopost_content_handler(update, context):
        return
    from handlers.admin_panel import admin_text_handler
    if await admin_text_handler(update, context):
        return


async def handle_media_message(update: Update, context):
    """Route media messages to appropriate handlers."""
    from handlers.welcome_dm import welcome_message_handler
    if await welcome_message_handler(update, context):
        return
    from handlers.broadcast import broadcast_message_handler
    if await broadcast_message_handler(update, context):
        return
    from handlers.template_mgmt import template_content_handler
    if await template_content_handler(update, context):
        return


def main():
    """Start the bot."""
    Config.validate()
    app = Application.builder().token(Config.BOT_TOKEN).post_init(post_init).build()

    # Import handlers
    from handlers.start import start_command, help_command
    from handlers.callbacks import callback_router
    from handlers.channel_settings import show_channels_list
    from handlers.user_commands import referral_command, stats_command, setdrip_command
    from handlers.template_mgmt import new_template_cmd, del_template_cmd
    from handlers.clone_bot import clone_command
    from handlers.auto_poster import autopost_cmd
    from handlers.admin_panel import admin_command

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("channels", lambda u, c: show_channels_list(u, c, is_command=True)))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("setdrip", setdrip_command))
    app.add_handler(CommandHandler("newtemplate", new_template_cmd))
    app.add_handler(CommandHandler("deltemplate", del_template_cmd))
    app.add_handler(CommandHandler("clone", clone_command))
    app.add_handler(CommandHandler("autopost", autopost_cmd))

    # Callback query router
    app.add_handler(CallbackQueryHandler(callback_router))

    # Join request handler
    app.add_handler(ChatJoinRequestHandler(handle_join_request))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media_message))

    logger.info("Starting bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
