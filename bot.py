"""Telegram Growth Engine - Main bot entry point."""
import logging
import asyncio
import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatJoinRequestHandler, filters,
    ChatMemberHandler
)
from config import Config
from database.connection import init_db
from database.init_tables import run_migrations
from handlers.start import start_command, help_command, dashboard_command
from handlers.channel_detection import channel_detection_handler
from handlers.join_request import join_request_handler
from handlers.callbacks import callback_router
from handlers.user_commands import stats_command, referral_command, setdrip_command
from handlers.admin_panel import admin_ban_command, admin_unban_command, admin_set_tier_command
from services.scheduler import setup_scheduler
from services.health_server import start_health_server

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot."""
    init_db()
    logger.info("Database initialized")

    port = int(os.getenv("PORT", "10000"))
    start_health_server(port)
    logger.info(f"Health server running on port {port}")

    app = Application.builder().token(Config.BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("setdrip", setdrip_command))
    app.add_handler(CommandHandler("ban", admin_ban_command))
    app.add_handler(CommandHandler("unban", admin_unban_command))
    app.add_handler(CommandHandler("settier", admin_set_tier_command))

    # Chat member updates
    app.add_handler(ChatMemberHandler(channel_detection_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    # Join requests
    app.add_handler(ChatJoinRequestHandler(join_request_handler))

    # All callback queries
    app.add_handler(CallbackQueryHandler(callback_router))

    # Text messages for stateful flows (private chat only)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_text_message
    ))

    # Scheduler
    setup_scheduler(app)

    # Post-init
    async def post_init(application):
        await run_migrations()
        logger.info("Post-init migrations complete")

    app.post_init = post_init

    logger.info("Starting bot in polling mode...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


async def handle_text_message(update: Update, context):
    """Route text messages based on user state."""
    if not update.message or not update.message.text:
        return

    ud = context.user_data
    state = ud.get("state")

    if state == "awaiting_broadcast_message" or ud.get("bc_setup"):
        from handlers.broadcast import broadcast_message_handler
        await broadcast_message_handler(update, context)
    elif state == "awaiting_template_body" or ud.get("creating_template"):
        from handlers.template_mgmt import template_content_handler
        await template_content_handler(update, context)
    elif state == "awaiting_autopost_message" or ud.get("autopost_setup"):
        from handlers.auto_poster import autopost_content_handler
        await autopost_content_handler(update, context)
    elif state == "awaiting_welcome_dm" or ud.get("editing_welcome_for"):
        from handlers.welcome_dm import welcome_message_handler
        await welcome_message_handler(update, context)
    elif ud.get("fs_add_for"):
        from handlers.force_subscribe import handle_force_sub_add
        await handle_force_sub_add(update, context)
    elif ud.get("admin_broadcast"):
        from handlers.admin_panel import admin_broadcast_handler
        await admin_broadcast_handler(update, context)
    elif ud.get("editing_setting"):
        from handlers.admin_panel import admin_setting_handler
        await admin_setting_handler(update, context)


if __name__ == "__main__":
    main()
