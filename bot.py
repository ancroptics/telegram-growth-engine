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


def main():
    app = (
        ApplicationBuilder.token(Config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ──────────────────────────────────────
    # Command handlers
    # ──────────────────────────────────────
    from handlers.start import start_command
    from handlers.help import help_command
    from handlers.settings import settings_command
    from handlers.stats import stats_command
    from handlers.broadcast import broadcast_command
    from handlers.export_data import export_command

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("export", export_command))

    # ──────────────────────────────────────
    # Callback query handler (single router)
    # ──────────────────────────────────────
    from handlers.callbacks import button_callback
    app.add_handler(CallbackQueryHandler(button_callback))

    # ──────────────────────────────────────
    # Chat join request handler
    # ──────────────────────────────────────
    from handlers.join_request import handle_join_request
    app.add_handler(ChatJoinRequestHandler(handle_join_request))

    # ──────────────────────────────────────
    # Chat member updates (detect bot added/removed from channels)
    # ──────────────────────────────────────
    from handlers.channel_detection import handle_my_chat_member
    app.add_handler(ChatMemberHandler(
        handle_my_chat_member,
        chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER
    ))

    # ──────────────────────────────────────
    # Message handlers for multi-step flows
    # ──────────────────────────────────────
    from handlers.clone import handle_clone_url
    from handlers.welcome import handle_welcome_text
    from handlers.broadcast import handle_broadcast_content

    app.add_handler(MessageHandler(
        handle_clone_url,
        filters.TEXT & filters.Regex(r'https?://(t\.me|telegram\.me)/')
    ))
    app.add_handler(MessageHandler(
        handle_welcome_text,
        filters.TEXT & ~filters.COMMAND,
        group=1
    ))
    app.add_handler(MessageHandler(
        handle_broadcast_content,
        filters.ALL & ~filters.COMMAND,
        group=2
    ))

    logger.info("Starting bot...")
    app.run_polling(
        allowed_updates=[
            "message", "callback_query", "chat_join_request",
            "my_chat_member", "chat_member"
        ],
        drop_pending_updates=True
    )


if __name__ == '__main__':
    main()
