"""Main entry point for Telegram Growth Engine."""
import asyncio
import logging
import sys
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ChatJoinRequestHandler, ChatMemberHandler, MessageHandler, filters
)
from config import Config
from database.connection import Database
from services.health_server import start_health_server
from services.scheduler import setup_scheduler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger(__name__)

async def post_init(app):
    """Initialize after app starts."""
    await Database.run_migrations()
    logger.info("Database initialized")
    setup_scheduler(app)
    logger.info("Scheduler started")

def setup_handlers(app):
    """Register all handlers."""
    from handlers.start import start_command, help_command, dashboard_command
    from handlers.callbacks import callback_router
    from handlers.join_request import join_request_handler
    from handlers.channel_detection import channel_detection_handler
    from handlers.user_commands import referral_command, stats_command, setdrip_command
    from handlers.broadcast import broadcast_message_handler
    from handlers.template_mgmt import new_template_cmd, del_template_cmd, template_content_handler
    from handlers.auto_poster import autopost_cmd, autopost_content_handler
    from handlers.clone_bot import clone_command, clone_token_handler
    from handlers.admin_panel import admin_ban_command, admin_unban_command, admin_set_tier_command, admin_broadcast_handler
    from handlers.welcome_dm import welcome_message_handler

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("setdrip", setdrip_command))
    app.add_handler(CommandHandler("newtemplate", new_template_cmd))
    app.add_handler(CommandHandler("deltemplate", del_template_cmd))
    app.add_handler(CommandHandler("autopost", autopost_cmd))
    app.add_handler(CommandHandler("clone", clone_command))
    app.add_handler(CommandHandler("ban", admin_ban_command))
    app.add_handler(CommandHandler("unban", admin_unban_command))
    app.add_handler(CommandHandler("settier", admin_set_tier_command))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_router))

    # Join requests
    app.add_handler(ChatJoinRequestHandler(join_request_handler))

    # Channel detection
    app.add_handler(ChatMemberHandler(channel_detection_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    # Message handlers (order matters - specific first)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        message_router
    ))
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.Document.ALL) & filters.ChatType.PRIVATE,
        media_router
    ))

async def message_router(update, context):
    """Route text messages to appropriate handlers."""
    from handlers.admin_panel import admin_broadcast_handler
    from handlers.broadcast import broadcast_message_handler
    from handlers.template_mgmt import template_content_handler
    from handlers.auto_poster import autopost_content_handler
    from handlers.clone_bot import clone_token_handler
    from handlers.welcome_dm import welcome_message_handler

    handlers = [
        admin_broadcast_handler,
        broadcast_message_handler,
        template_content_handler,
        autopost_content_handler,
        clone_token_handler,
        welcome_message_handler,
    ]
    for handler in handlers:
        try:
            if await handler(update, context):
                return
        except Exception as e:
            logger.error(f"Handler error: {e}")

async def media_router(update, context):
    """Route media messages."""
    from handlers.broadcast import broadcast_message_handler
    from handlers.template_mgmt import template_content_handler
    from handlers.welcome_dm import welcome_message_handler

    for handler in [broadcast_message_handler, template_content_handler, welcome_message_handler]:
        try:
            if await handler(update, context):
                return
        except Exception as e:
            logger.error(f"Media handler error: {e}")

def main():
    """Start the bot."""
    logger.info(f"Starting Telegram Growth Engine v3.0")
    logger.info(f"Bot: @{Config.BOT_USERNAME or 'unknown'}")

    app = (
        ApplicationBuilder()
        .token(Config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    setup_handlers(app)

    # Start health server in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        await start_health_server()
        logger.info("Health server started")
        async with app:
            await app.start()
            logger.info("Bot started polling")
            await app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "chat_join_request", "my_chat_member"]
            )
            # Keep running
            stop_event = asyncio.Event()
            await stop_event.wait()

    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
