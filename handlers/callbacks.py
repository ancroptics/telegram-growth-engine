"""Callback query router."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all callback queries to appropriate handlers."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    data = query.data

    try:
        # Main menu
        if data == "main_menu":
            from handlers.start import start_command
            # Fake an update with a message to reuse start
            from utils.keyboards import main_menu_kb
            from config import Config
            is_admin = update.effective_user.id in Config.ADMIN_IDS or update.effective_user.id in Config.SUPERADMIN_IDS
            await query.message.edit_text(
                "\ud83c\udf1f <b>Telegram Growth Engine</b>\n\nSelect an option:",
                parse_mode="HTML",
                reply_markup=main_menu_kb(is_admin)
            )

        # Channel management
        elif data in ("my_channels", "add_channel") or data.startswith(("manage_ch:", "ch_toggle:", "ch_delete:", "ch_confirm_delete:")):
            from handlers.channel_settings import handle_channel_callback
            await handle_channel_callback(update, context)

        # Welcome DM editing
        elif data.startswith("ch_edit_welcome:"):
            from handlers.welcome_dm import handle_welcome_dm_callback
            await handle_welcome_dm_callback(update, context)

        # Force subscribe
        elif data.startswith(("ch_force_sub:", "fs_")):
            from handlers.force_subscribe import handle_force_sub_callback
            await handle_force_sub_callback(update, context)

        # Broadcast
        elif data in ("broadcast_menu",) or data.startswith("bc_"):
            from handlers.broadcast import handle_broadcast_callback
            await handle_broadcast_callback(update, context)

        # Templates
        elif data in ("template_settings", "templates_list") or data.startswith("tpl_"):
            from handlers.template_mgmt import handle_template_callback
            await handle_template_callback(update, context)

        # Auto poster
        elif data in ("auto_poster",) or data.startswith("ap_"):
            from handlers.auto_poster import handle_auto_poster_callback
            await handle_auto_poster_callback(update, context)

        # Analytics
        elif data.startswith("ch_analytics:") or data == "analytics":
            from handlers.analytics_view import handle_analytics_callback
            await handle_analytics_callback(update, context)

        # Batch approve
        elif data.startswith("ch_pending:") or data.startswith("batch_"):
            from handlers.batch_approve import handle_batch_callback
            await handle_batch_callback(update, context)

        # Premium
        elif data in ("premium_info", "premium_buy") or data.startswith("premium_"):
            from handlers.premium import handle_premium_callback
            await handle_premium_callback(update, context)

        # Clone bot
        elif data in ("clone_bot",) or data.startswith("clone_"):
            from handlers.clone_bot import handle_clone_callback
            await handle_clone_callback(update, context)

        # Cross promo
        elif data in ("cross_promo",) or data.startswith("xpromo_"):
            from handlers.cross_promo import handle_cross_promo_callback
            await handle_cross_promo_callback(update, context)

        # Admin panel
        elif data.startswith("admin_"):
            from handlers.admin_panel import handle_admin_callback
            await handle_admin_callback(update, context)

        # User management
        elif data.startswith("user_"):
            from handlers.user_mgmt import handle_user_mgmt_callback
            await handle_user_mgmt_callback(update, context)

        # Language
        elif data.startswith("lang_"):
            from handlers.language_mgmt import handle_language_callback
            await handle_language_callback(update, context)

        # Support
        elif data == "support":
            await query.message.edit_text(
                "\ud83d\udcac <b>Support</b>\n\nFor help, contact @TGESupport",
                parse_mode="HTML",
                reply_markup=__import__('telegram', fromlist=['InlineKeyboardMarkup']).InlineKeyboardMarkup(
                    [[__import__('telegram', fromlist=['InlineKeyboardButton']).InlineKeyboardButton("\u00ab Back", callback_data="main_menu")]]
                )
            )

        else:
            logger.warning(f"Unhandled callback: {data}")

    except Exception as e:
        logger.error(f"Callback error for '{data}': {e}", exc_info=True)
        try:
            await query.message.edit_text(f"\u26a0\ufe0f Error processing request. Please try again.")
        except Exception:
            pass
