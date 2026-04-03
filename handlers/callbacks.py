"""Callback query router."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route ALL callback queries to the appropriate handler."""
    query = update.callback_query
    data = query.data or ""

    try:
        await query.answer()
    except Exception:
        pass

    try:
        # ── Navigation ──
        if data in ("back_to_main", "main_menu"):
            from handlers.start import show_main_menu
            return await show_main_menu(update, context)

        if data == "support":
            from handlers.start import show_support
            return await show_support(update, context)

        # ── Channel management ──
        if data in ("my_channels", "add_channel") or data.startswith(("manage_ch:", "ch_settings:", "ch_toggle:", "ch_delete:", "ch_confirm_delete:")):
            from handlers.channel_settings import handle_channel_callback
            return await handle_channel_callback(update, context)

        # ── Welcome DM ──
        if data.startswith("ch_edit_welcome:") or data.startswith("welcome_"):
            from handlers.welcome_dm import handle_welcome_dm_callback
            return await handle_welcome_dm_callback(update, context)

        # ── Broadcast ──
        if data in ("broadcast_menu",) or data.startswith("bc_"):
            from handlers.broadcast import handle_broadcast_callback
            return await handle_broadcast_callback(update, context)

        # ── Template ──
        if data in ("template_settings", "templates_list") or data.startswith("tmpl_"):
            from handlers.template_mgmt import handle_template_callback
            return await handle_template_callback(update, context)

        # ── Admin / Superadmin panel ──
        if data in ("admin_panel", "superadmin") or data.startswith(("admin_", "sa_")):
            from handlers.admin_panel import handle_admin_callback
            return await handle_admin_callback(update, context)

        # ── Premium ──
        if data in ("premium_info",) or data.startswith(("prem_", "premium_")):
            from handlers.premium import handle_premium_callback
            return await handle_premium_callback(update, context)

        # ── Clone bot ──
        if data in ("clone_bot", "clone_list") or data.startswith("clone_"):
            from handlers.clone_bot import handle_clone_callback
            return await handle_clone_callback(update, context)

        # ── Analytics + Export ──
        if data in ("analytics", "analytics_overview") or data.startswith(("analytics_", "ch_analytics:", "ch_export:")):
            from handlers.analytics_view import handle_analytics_callback
            return await handle_analytics_callback(update, context)

        # ── Force subscribe ──
        if data.startswith(("fs_verify:", "fs_toggle:", "fs_add:", "ch_force_sub:", "fs_remove:")):
            from handlers.force_subscribe import handle_force_sub_callback
            return await handle_force_sub_callback(update, context)

        # ── Batch approve / Drip / Pending ──
        if data.startswith(("batch_", "drip_", "ch_pending:")):
            from handlers.batch_approve import handle_batch_callback
            return await handle_batch_callback(update, context)

        # ── Cross promo ──
        if data in ("cross_promo",) or data.startswith(("xp_", "cp_cat:", "ch_cross_promo:")):
            from handlers.cross_promo import handle_cross_promo_callback
            return await handle_cross_promo_callback(update, context)

        # ── Auto poster ──
        if data in ("auto_poster",) or data.startswith("ap_"):
            from handlers.auto_poster import handle_auto_poster_callback
            return await handle_auto_poster_callback(update, context)

        # ── User management ──
        if data in ("user_mgmt",) or data.startswith("um_"):
            from handlers.user_mgmt import handle_user_mgmt_callback
            return await handle_user_mgmt_callback(update, context)

        # ── Language ──
        if data.startswith(("lang_", "ch_i18n:")):
            from handlers.language_mgmt import handle_language_callback
            return await handle_language_callback(update, context)

        # ── Close ──
        if data == "close":
            try:
                await query.message.delete()
            except Exception:
                pass
            return

        logger.warning(f"Unhandled callback: {data}")

    except ImportError as e:
        logger.error(f"Handler import error for \"{data}\": {e}")
        try:
            await query.message.reply_text("⚠️ Feature not available yet.")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Callback error \"{data}\": {e}", exc_info=True)
        try:
            await query.message.reply_text("⚠️ Error occurred. Try /start.")
        except Exception:
            pass
