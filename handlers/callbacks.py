"""Central callback query router."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if not data:
        await query.answer()
        return

    try:
        # Route based on callback data prefix
        if data == "main_menu":
            from handlers.start import show_main_menu
            await show_main_menu(update, context)
        elif data in ("my_channels", "add_channel") or data.startswith(("manage_ch:", "ch_delete:", "ch_confirm_delete:")):
            from handlers.channel_settings import handle_channel_callback
            await handle_channel_callback(update, context)
        elif data.startswith(("ch_pending:", "batch_approve:", "batch_decline:", "drip_start:", "drip_config:")):
            from handlers.batch_approve import handle_batch_callback
            await handle_batch_callback(update, context)
        elif data.startswith(("ch_edit_welcome:",)):
            from handlers.welcome_dm import handle_welcome_dm_callback
            await handle_welcome_dm_callback(update, context)
        elif data.startswith(("ch_settings:", "ch_toggle:", "ch_set_rate:")):
            from handlers.channel_settings import handle_channel_callback
            await handle_channel_callback(update, context)
        elif data.startswith(("ch_force_sub:", "fs_toggle:", "fs_add:", "fs_verify:")):
            from handlers.force_subscribe import handle_force_sub_callback
            await handle_force_sub_callback(update, context)
        elif data.startswith(("ch_analytics:", "ch_export:")) or data == "analytics_overview":
            from handlers.analytics_view import handle_analytics_callback
            await handle_analytics_callback(update, context)
        elif data.startswith(("ch_i18n:",)):
            from handlers.language_mgmt import handle_language_callback
            await handle_language_callback(update, context)
        elif data.startswith(("broadcast_", "bc_")):
            from handlers.broadcast import handle_broadcast_callback
            await handle_broadcast_callback(update, context)
        elif data == "templates_list":
            from handlers.template_mgmt import handle_template_callback
            await handle_template_callback(update, context)
        elif data == "auto_poster":
            from handlers.auto_poster import handle_auto_poster_callback
            await handle_auto_poster_callback(update, context)
        elif data.startswith(("clone_",)):
            from handlers.clone_bot import handle_clone_callback
            await handle_clone_callback(update, context)
        elif data.startswith(("premium_",)):
            from handlers.premium import handle_premium_callback
            await handle_premium_callback(update, context)
        elif data in ("cross_promo",) or data.startswith(("ch_cross_promo:", "cp_cat:")):
            from handlers.cross_promo import handle_cross_promo_callback
            await handle_cross_promo_callback(update, context)
        elif data.startswith(("superadmin", "sa_")):
            from handlers.admin_panel import handle_admin_callback
            await handle_admin_callback(update, context)
        elif data == "user_mgmt":
            from handlers.user_mgmt import handle_user_mgmt_callback
            await handle_user_mgmt_callback(update, context)
        else:
            logger.warning(f"Unhandled callback: {data}")
            await query.answer("Unknown action", show_alert=True)
    except Exception as e:
        logger.error(f"Callback error for '{data}': {e}", exc_info=True)
        try:
            await query.answer(f"Error: {str(e)[:100]}", show_alert=True)
        except Exception:
            pass
