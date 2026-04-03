"""Main entry point for Telegram Growth Engine."""
import asyncio
import logging
import sys
import traceback
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ChatJoinRequestHandler, ChatMemberHandler, MessageHandler, filters
)
from config import Config
from database.connection import Database
from services.health_server import start_health_server
from services.scheduler import setup_scheduler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger(__name__)

async def post_init(app):
    try:
        await Database.run_migrations()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database migration error: {e}")
    try:
        setup_scheduler(app)
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
    try:
        bot_info = await app.bot.get_me()
        Config.BOT_USERNAME = bot_info.username
        logger.info(f"Bot username: @{Config.BOT_USERNAME}")
    except Exception as e:
        logger.error(f"get_me error: {e}")

def setup_handlers(app):
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
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(ChatJoinRequestHandler(join_request_handler))
    app.add_handler(ChatMemberHandler(channel_detection_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        message_router
    ))
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.Document.ALL) & filters.ChatType.PRIVATE,
        media_router
    ))

async def message_router(update, context):
    from handlers.admin_panel import admin_broadcast_handler
    from handlers.broadcast import broadcast_message_handler
    from handlers.template_mgmt import template_content_handler
    from handlers.auto_poster import autopost_content_handler
    from handlers.clone_bot import clone_token_handler
    from handlers.welcome_dm import welcome_message_handler
    for handler in [admin_broadcast_handler, broadcast_message_handler, template_content_handler, autopost_content_handler, clone_token_handler, welcome_message_handler]:
        try:
            if await handler(update, context):
                return
        except Exception as e:
            logger.error(f"Handler error: {e}")

async def media_router(update, context):
    from handlers.broadcast import broadcast_message_handler
    from handlers.template_mgmt import template_content_handler
    from handlers.welcome_dm import welcome_message_handler
    for handler in [broadcast_message_handler, template_content_handler, welcome_message_handler]:
        try:
            if await handler(update, context):
                return
        except Exception as e:
            logger.error(f"Media handler error: {e}")

async def run_bot():
    """Run both health server and bot in the same event loop."""
    logger.info("Starting Telegram Growth Engine v3.0")
    if not Config.BOT_TOKEN:
        logger.critical("BOT_TOKEN not set! Exiting.")
        sys.exit(1)

    # Start health server
    try:
        runner = await start_health_server()
        logger.info("Health server started")
    except Exception as e:
        logger.error(f"Health server failed: {e}")

    # Build bot application
    app = (
        ApplicationBuilder()
        .token(Config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    setup_handlers(app)

    logger.info("Starting bot polling...")
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "chat_join_request", "my_chat_member"]
        )
        logger.info("Bot polling started successfully!")
        # Keep running forever
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.critical(f"Bot polling failed: {e}")
        traceback.print_exc()
        # Keep health server alive so we can see the error in logs
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_bot())
