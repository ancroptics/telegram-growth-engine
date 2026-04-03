"""Callback query handler for inline keyboard buttons."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to appropriate handlers."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Failed to answer callback query: {e}")
    
    data = query.data
    
    try:
        if data == "admin_panel":
            from handlers.admin_panel import show_admin_panel
            await show_admin_panel(update, context)
        
        elif data == "force_sub_settings":
            from handlers.force_subscribe import show_force_sub_settings
            await show_force_sub_settings(update, context)
        
        elif data == "broadcast_menu":
            from handlers.broadcast import show_broadcast_menu
            await show_broadcast_menu(update, context)
        
        elif data == "analytics":
            from handlers.analytics_view import show_analytics
            await show_analytics(update, context)
        
        elif data == "channel_settings":
            from handlers.channel_settings import show_channel_settings
            await show_channel_settings(update, context)
        
        elif data == "template_settings":
            from handlers.template_mgmt import show_template_settings
            await show_template_settings(update, context)
        
        elif data == "language_settings":
            from handlers.language_mgmt import show_language_settings
            await show_language_settings(update, context)
        
        elif data == "clone_bot":
            from handlers.clone_bot import show_clone_menu
            await show_clone_menu(update, context)
        
        elif data == "premium_info":
            from handlers.premium import show_premium_info
            await show_premium_info(update, context)
        
        elif data == "user_management":
            from handlers.user_mgmt import show_user_management
            await show_user_management(update, context)
        
        elif data == "cross_promo":
            from handlers.cross_promo import show_cross_promo
            await show_cross_promo(update, context)
        
        elif data == "batch_approve":
            from handlers.batch_approve import show_batch_approve
            await show_batch_approve(update, context)
        
        elif data.startswith("approve_"):
            from handlers.join_request import approve_request_callback
            await approve_request_callback(update, context)
        
        elif data == "back_to_main":
            from handlers.start import send_main_menu
            await send_main_menu(update, context, edit=True)
        
        elif data == "back_to_admin":
            from handlers.admin_panel import show_admin_panel
            await show_admin_panel(update, context)
        
        elif data == "close":
            try:
                await query.message.delete()
            except Exception:
                pass
        
        else:
            logger.warning(f"Unknown callback data: {data}")
            await query.message.reply_text("\u26a0\ufe0f Unknown action. Please try again.")
    
    except Exception as e:
        logger.error(f"Error handling callback \"{data}\": {e}", exc_info=True)
        try:
            await query.message.reply_text(
                "\u26a0\ufe0f An error occurred. Please try again or use /start."
            )
        except Exception:
            pass
