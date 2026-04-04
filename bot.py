"""Main bot entry point."""
import sys, logging, asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
    ChatJoinRequestHandler, ChatMemberHandler, MessageHandler, filters)
from config import BOT_TOKEN, PORT, ADMIN_IDS

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

async def health_handler(request):
    return web.Response(text="OK", status=200)

async def run_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"Health server on port {PORT}")

def setup_handlers(application):
    from handlers.start import start_command, help_command, main_menu_callback
    from handlers.channels import (my_channels_callback, channel_settings_callback,
        toggle_approve_callback, toggle_welcome_callback, edit_welcome_callback,
        approve_mode_callback, set_mode_callback, handle_my_chat_member, handle_welcome_message_input)
    from handlers.join_requests import handle_join_request
    from handlers.broadcast import (broadcast_menu_callback, bc_channel_callback, bc_global_callback, handle_broadcast_input)
    from handlers.analytics import analytics_menu_callback, channel_analytics_callback, stats_command
    from handlers.premium import premium_menu_callback, upgrade_callback, referral_menu_callback
    from handlers.admin import admin_panel_callback, admin_channels_callback, ban_command, unban_command, setpremium_command
    from handlers.settings import settings_callback
    from handlers.templates import (templates_menu_callback, create_tpl_callback, handle_template_input, view_tpl_callback, del_tpl_callback)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("setpremium", setpremium_command))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(my_channels_callback, pattern="^my_channels$"))
    application.add_handler(CallbackQueryHandler(channel_settings_callback, pattern="^ch_settings:"))
    application.add_handler(CallbackQueryHandler(toggle_approve_callback, pattern="^toggle_approve:"))
    application.add_handler(CallbackQueryHandler(toggle_welcome_callback, pattern="^toggle_welcome:"))
    application.add_handler(CallbackQueryHandler(edit_welcome_callback, pattern="^edit_welcome:"))
    application.add_handler(CallbackQueryHandler(approve_mode_callback, pattern="^approve_mode:"))
    application.add_handler(CallbackQueryHandler(set_mode_callback, pattern="^set_mode:"))
    application.add_handler(CallbackQueryHandler(broadcast_menu_callback, pattern="^broadcast_menu$"))
    application.add_handler(CallbackQueryHandler(bc_channel_callback, pattern="^bc_channel:"))
    application.add_handler(CallbackQueryHandler(bc_global_callback, pattern="^bc_global$"))
    application.add_handler(CallbackQueryHandler(analytics_menu_callback, pattern="^analytics_menu$"))
    application.add_handler(CallbackQueryHandler(channel_analytics_callback, pattern="^ch_analytics:"))
    application.add_handler(CallbackQueryHandler(premium_menu_callback, pattern="^premium_menu$"))
    application.add_handler(CallbackQueryHandler(upgrade_callback, pattern="^upgrade_"))
    application.add_handler(CallbackQueryHandler(referral_menu_callback, pattern="^referral_menu$"))
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_channels_callback, pattern="^admin_channels$"))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(templates_menu_callback, pattern="^templates_menu$"))
    application.add_handler(CallbackQueryHandler(create_tpl_callback, pattern="^create_tpl$"))
    application.add_handler(CallbackQueryHandler(view_tpl_callback, pattern="^view_tpl:"))
    application.add_handler(CallbackQueryHandler(del_tpl_callback, pattern="^del_tpl:"))
    application.add_handler(CallbackQueryHandler(lambda u,c: u.callback_query.answer() or help_command(u,c), pattern="^help_menu$"))

    async def handle_text_input(update, context):
        if not update.message: return
        if await handle_welcome_message_input(update, context): return
        if await handle_template_input(update, context): return
        if await handle_broadcast_input(update, context): return

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_text_input))
    application.add_handler(MessageHandler((filters.PHOTO | filters.VIDEO | filters.Document.ALL) & filters.ChatType.PRIVATE, handle_broadcast_input))
    logger.info("All handlers registered")

async def main():
    logger.info("Starting Telegram Growth Engine...")
    await run_health_server()
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    logger.info("Bot is running!")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
