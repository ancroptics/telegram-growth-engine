"""Telegram Growth Engine — Main bot entry point."""
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatJoinRequestHandler, filters,
    ChatMemberHandler
)
from config import Config
from database.connection import db
from handlers.start import start_command, help_command, dashboard_command
from handlers.channel_detection import my_chat_member_handler
from handlers.join_request import join_request_handler
from handlers.broadcast import (
    broadcast_start, broadcast_message, broadcast_confirm_handler
)
from handlers.callbacks import button_callback
from handlers.auto_poster import (
    autopost_command, autopost_set_message, autopost_set_interval,
    autopost_confirm_handler
)
from handlers.template_mgmt import new_template_command, del_template_command, template_body_handler
from handlers.user_commands import stats_command, referral_command, setdrip_command
from handlers.force_subscribe import force_sub_check
from handlers.welcome_dm import edit_welcome_message_handler
from handlers.admin_panel import admin_command, admin_callback_handler
from services.scheduler_service import setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot."""
    app = Application.builder().token(Config.BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("broadcast", broadcast_start))
    app.add_handler(CommandHandler("autopost", autopost_command))
    app.add_handler(CommandHandler("newtemplate", new_template_command))
    app.add_handler(CommandHandler("deltemplate", del_template_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("setdrip", setdrip_command))
    app.add_handler(CommandHandler("admin", admin_command))

    # Chat member updates (channel add/remove detection)
    app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    # Join requests
    app.add_handler(ChatJoinRequestHandler(join_request_handler))

    # Callback queries
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern=r"^admin_"))
    app.add_handler(CallbackQueryHandler(broadcast_confirm_handler, pattern=r"^bc_"))
    app.add_handler(CallbackQueryHandler(autopost_confirm_handler, pattern=r"^ap_"))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Message handlers (order matters — most specific first)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r"^/?"),
        handle_text_message
    ))

    # Force subscribe check on any group message
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & ~filters.COMMAND,
        force_sub_check
    ))

    # Scheduler for auto-posts and stats
    setup_scheduler(app)

    logger.info("🚀 Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route text messages based on user state."""
    if not update.message or not update.message.text:
        return

    user_data = context.user_data
    state = user_data.get("state")

    if state == "awaiting_broadcast_message":
        await broadcast_message(update, context)
    elif state == "awaiting_template_body":
        await template_body_handler(update, context)
    elif state == "awaiting_autopost_message":
        await autopost_set_message(update, context)
    elif state == "awaiting_autopost_interval":
        await autopost_set_interval(update, context)
    elif state == "awaiting_welcome_dm":
        await edit_welcome_message_handler(update, context)
    else:
        pass  # Ignore unrecognized text


if __name__ == "__main__":
    main()
