"""Analytics display."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_channel_stats, get_owner_channels, get_managed_channel
from utils.keyboards import back_kb
from utils.helpers import format_number

logger = logging.getLogger(__name__)

async def handle_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user
    await query.answer()

    if data == "analytics_overview":
        channels = await get_owner_channels(user.id)
        total_approved = sum(ch.get("total_approved", 0) for ch in channels)
        total_dms = sum(ch.get("total_dms_sent", 0) for ch in channels)
        text = (f"📊 <b>ANALYTICS OVERVIEW</b>\n\n"
                f"📢 Channels: {len(channels)}\n"
                f"✅ Total Approved: {format_number(total_approved)}\n"
                f"💬 Total DMs Sent: {format_number(total_dms)}\n\n")
        for ch in channels[:5]:
            text += f"📢 {ch.get('chat_title','?')[:20]}: ✅{format_number(ch.get('total_approved',0))} 💬{format_number(ch.get('total_dms_sent',0))}\n"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb())

    elif data.startswith("ch_analytics:"):
        chat_id = int(data.split(":")[1])
        channel = await get_managed_channel(chat_id)
        if not channel: return
        stats = await get_channel_stats(chat_id, 7)
        text = (f"📊 <b>{channel.get('chat_title','')} — Analytics</b>\n\n"
                f"━━━ ALL TIME ━━━\n"
                f"✅ Approved: {format_number(channel.get('total_approved',0))}\n"
                f"💬 DMs Sent: {format_number(channel.get('total_dms_sent',0))}\n\n")
        if stats:
            text += "━━━ LAST 7 DAYS ━━━\n"
            for s in stats:
                text += f"📅 {s.get('date')}: 📋{s.get('requests_received',0)} ✅{s.get('requests_approved',0)}\n"
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb(f"manage_ch:{chat_id}"))

    elif data.startswith("ch_export:"):
        chat_id = int(data.split(":")[1])
        stats = await get_channel_stats(chat_id, 90)
        if not stats:
            await query.message.edit_text("No data.", reply_markup=back_kb(f"manage_ch:{chat_id}"))
            return
        import io
        csv_lines = ["date,requests,approved,dms_sent"]
        for s in stats:
            csv_lines.append(f"{s['date']},{s.get('requests_received',0)},{s.get('requests_approved',0)},{s.get('dms_sent',0)}")
        buf = io.BytesIO("\n".join(csv_lines).encode())
        buf.name = f"analytics_{chat_id}.csv"
        await context.bot.send_document(update.effective_user.id, buf, caption="📊 Analytics export")
        await query.answer("📤 Export sent!", show_alert=True)
