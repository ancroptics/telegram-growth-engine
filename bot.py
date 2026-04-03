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
        await Database.get_pool()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
    try:
        setup_scheduler(app)
    except Exception as e:
        logger.error(f"Scheduler setup failed: {e}")


async def post_shutdown(app):
    await Database.close()


def main():
    Config.validate()

    app = (
        ApplicationBuilder()
        .token(Config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Command handlers
    from handlers.start import start_command, help_command, dashboard_command
    from handlers.user_commands import referral_command, stats_command, setdrip_command
    from handlers.admin_panel import admin_ban_command, admin_unban_command, admin_set_tier_command
    from handlers.template_mgmt import new_template_cmd, del_template_cmd
    from handlers.auto_poster import autopost_cmd

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("setdrip", setdrip_command))
    app.add_handler(CommandHandler("ban", admin_ban_command))
    app.add_handler(CommandHandler("unban", admin_unban_command))
    app.add_handler(CommandHandler("settier", admin_set_tier_command))
    app.add_handler(CommandHandler("newtemplate", new_template_cmd))
    app.add_handler(CommandHandler("deltemplate", del_template_cmd))
    app.add_handler(CommandHandler("autopost", autopost_cmd))

    # Callback query router
    from handlers.callbacks import callback_router
    app.add_handler(CallbackQueryHandler(callback_router))

    # Join request handler
    from handlers.join_request import join_request_handler
    app.add_handler(ChatJoinRequestHandler(join_request_handler))

    # Chat member updates
    from handlers.channel_detection import channel_detection_handler
    app.add_handler(ChatMemberHandler(
        channel_detection_handler,
        chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER
    ))

    # Text message handler
    async def text_message_handler(update, context):
        if context.user_data.get("fs_add_for"):
            from handlers.force_subscribe import handle_force_sub_add
            return await handle_force_sub_add(update, context)
        if context.user_data.get("editing_welcome_for"):
            from handlers.welcome_dm import welcome_message_handler
            return await welcome_message_handler(update, context)
        if context.user_data.get("bc_setup"):
            from handlers.broadcast import broadcast_message_handler
            return await broadcast_message_handler(update, context)
        if context.user_data.get("creating_template"):
            from handlers.template_mgmt import template_content_handler
            return await template_content_handler(update, context)
        if context.user_data.get("autopost_setup"):
            from handlers.auto_poster import autopost_content_handler
            return await autopost_content_handler(update, context)
        if context.user_data.get("admin_broadcast"):
            from handlers.admin_panel import admin_broadcast_handler
            return await admin_broadcast_handler(update, context)
        if context.user_data.get("editing_setting"):
            from handlers.admin_panel import admin_setting_handler
            return await admin_setting_handler(update, context)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    async def media_message_handler(update, context):
        if context.user_data.get("bc_setup"):
            from handlers.broadcast import broadcast_message_handler
            return await broadcast_message_handler(update, context)
        if context.user_data.get("creating_template"):
            from handlers.template_mgmt import template_content_handler
            return await template_content_handler(update, context)

    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND,
        media_message_handler
    ))

    logger.info("Starting bot in polling mode...")
    app.run_polling(
        allowed_updates=["message", "callback_query", "chat_join_request", "my_chat_member"],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
