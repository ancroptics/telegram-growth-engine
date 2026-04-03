"""Telegram Growth Engine — Main bot entry point."""
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatJoinRequestHandler,
    ChatMemberHandler, filters
)
from config import Config
from database.connection import init_db
from services.health_server import start_health_server
from services.scheduler import setup_scheduler

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


async def error_handler(update: object, context) -> None:
    """Global error handler."""
    logger.error(f"Exception: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "\u26a0\ufe0f Something went wrong. Please try again."
            )
        except Exception:
            pass


def main():
    """Initialize and run the bot."""
    if not Config.validate():
        logger.critical("Invalid configuration. Exiting.")
        return

    # Initialize DB
    init_db()
    logger.info("Database initialized")

    # Build application
    app = Application.builder().token(Config.BOT_TOKEN).build()

    # --- Import handlers ---
    from handlers.start import start_command, help_command, dashboard_command
    from handlers.callbacks import callback_router
    from handlers.join_request import join_request_handler
    from handlers.channel_detection import channel_detection_handler
    from handlers.user_commands import referral_command, stats_command, setdrip_command
    from handlers.admin_panel import (
        admin_ban_command, admin_unban_command, admin_set_tier_command,
        admin_broadcast_handler, admin_setting_handler
    )
    from handlers.template_mgmt import (
        new_template_cmd, del_template_cmd, template_content_handler
    )
    from handlers.auto_poster import autopost_cmd, autopost_content_handler
    from handlers.broadcast import broadcast_message_handler
    from handlers.welcome_dm import welcome_message_handler
    from handlers.force_subscribe import handle_force_sub_add

    # --- Command handlers ---
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("setdrip", setdrip_command))
    app.add_handler(CommandHandler("newtemplate", new_template_cmd))
    app.add_handler(CommandHandler("deltemplate", del_template_cmd))
    app.add_handler(CommandHandler("autopost", autopost_cmd))

    # Admin commands
    app.add_handler(CommandHandler("ban", admin_ban_command))
    app.add_handler(CommandHandler("unban", admin_unban_command))
    app.add_handler(CommandHandler("settier", admin_set_tier_command))

    # --- Callback query handler (routes all button presses) ---
    app.add_handler(CallbackQueryHandler(callback_router))

    # --- Join request handler ---
    app.add_handler(ChatJoinRequestHandler(join_request_handler))

    # --- Chat member handler (bot added/removed from channels) ---
    app.add_handler(ChatMemberHandler(channel_detection_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    # --- Message handlers (order matters — most specific first) ---
    # Template content (user is creating a template)
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & filters.ChatType.PRIVATE,
        _text_message_router
    ))

    # Error handler
    app.add_error_handler(error_handler)

    # Setup scheduler
    setup_scheduler(app)

    # Run with webhook or polling
    if Config.WEBHOOK_URL:
        logger.info(f"Starting webhook mode on {Config.HOST}:{Config.PORT}")
        # Start health server in background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        app.run_webhook(
            listen=Config.HOST,
            port=Config.PORT,
            url_path=Config.WEBHOOK_PATH,
            webhook_url=f"{Config.WEBHOOK_URL}{Config.WEBHOOK_PATH}",
            secret_token=Config.WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
    else:
        logger.info("Starting polling mode")
        app.run_polling(drop_pending_updates=True)


async def _text_message_router(update: Update, context) -> None:
    """Route text messages based on user_data state."""
    from handlers.admin_panel import admin_broadcast_handler, admin_setting_handler
    from handlers.template_mgmt import template_content_handler
    from handlers.auto_poster import autopost_content_handler
    from handlers.broadcast import broadcast_message_handler
    from handlers.welcome_dm import welcome_message_handler
    from handlers.force_subscribe import handle_force_sub_add

    ud = context.user_data or {}

    if ud.get("admin_broadcast"):
        await admin_broadcast_handler(update, context)
    elif ud.get("editing_setting"):
        await admin_setting_handler(update, context)
    elif ud.get("creating_template"):
        await template_content_handler(update, context)
    elif ud.get("autopost_setup"):
        await autopost_content_handler(update, context)
    elif ud.get("bc_setup"):
        await broadcast_message_handler(update, context)
    elif ud.get("editing_welcome_for"):
        await welcome_message_handler(update, context)
    elif ud.get("fs_add_for"):
        await handle_force_sub_add(update, context)
    else:
        # Default: no active state, ignore or show help
        pass


if __name__ == "__main__":
    main()
