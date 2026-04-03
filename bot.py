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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger(__name__)


async def post_init(app):
    try:
        await start_health_server()
    except Exception as e:
        logger.error(f"Health server failed: {e}")

    try:
        db = Database()
        await db.initialize()
        app.bot_data['db'] = db
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

    try:
        setup_scheduler(app)
    except Exception as e:
        logger.error(f"Scheduler setup failed: {e}")


async def post_shutdown(app):
    db = app.bot_data.get('db')
    if db:
        await db.close()
        logger.info("Database connection closed")


def main():
    app = (
        ApplicationBuilder()
        .token(Config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    from handlers.start import start_command, handle_deep_link
    from handlers.callbacks import button_callback
    from handlers.admin_panel import admin_command
    from handlers.force_subscribe import (
        force_sub_command, set_channel_command, remove_channel_command,
        check_membership
    )
    from handlers.clone_bot import clone_command, handle_clone_token
    from handlers.broadcast import broadcast_command, handle_broadcast_message
    from handlers.join_request import handle_join_request, approve_request_callback
    from handlers.channel_detection import handle_new_chat_member
    from handlers.channel_settings import channel_settings_command
    from handlers.analytics_view import analytics_command
    from handlers.batch_approve import batch_approve_command
    from handlers.user_commands import (
        my_referrals_command, leaderboard_command, help_command
    )
    from handlers.template_mgmt import template_command
    from handlers.language_mgmt import language_command
    from handlers.welcome_dm import handle_welcome_trigger

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("forcesub", force_sub_command))
    app.add_handler(CommandHandler("setchannel", set_channel_command))
    app.add_handler(CommandHandler("removechannel", remove_channel_command))
    app.add_handler(CommandHandler("clone", clone_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("settings", channel_settings_command))
    app.add_handler(CommandHandler("analytics", analytics_command))
    app.add_handler(CommandHandler("batchapprove", batch_approve_command))
    app.add_handler(CommandHandler("referrals", my_referrals_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("template", template_command))
    app.add_handler(CommandHandler("language", language_command))

    # Callback query handler
    app.add_handler(CallbackQueryHandler(button_callback))

    # Join request handler
    app.add_handler(ChatJoinRequestHandler(handle_join_request))

    # Chat member handler
    app.add_handler(ChatMemberHandler(
        handle_new_chat_member, ChatMemberHandler.CHAT_MEMBER
    ))

    # Message handlers
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_clone_token
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_broadcast_message
    ))

    logger.info("Bot starting...")
    if Config.USE_WEBHOOK and Config.WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=Config.PORT,
            url_path=Config.BOT_TOKEN,
            webhook_url=f"{Config.WEBHOOK_URL}/{Config.BOT_TOKEN}"
        )
    else:
        app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query", "chat_join_request", "chat_member"])


if __name__ == "__main__":
    main()
