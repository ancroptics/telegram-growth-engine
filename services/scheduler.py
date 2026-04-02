"""APScheduler background jobs."""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram.ext import Application

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def drip_approve_job(app: Application):
    from database.models import get_drip_channels, get_pending_requests, approve_join_request_db
    from telegram.error import BadRequest, RetryAfter
    channels = await get_drip_channels()
    now = datetime.now()
    for ch in channels:
        if now.hour < ch.get("drip_active_start", 8) or now.hour >= ch.get("drip_active_end", 23): continue
        rate = ch.get("drip_rate", 50)
        pending = await get_pending_requests(ch["chat_id"], limit=rate)
        for req in pending:
            try:
                await app.bot.approve_chat_join_request(ch["chat_id"], req["user_id"])
                await approve_join_request_db(req["user_id"], ch["chat_id"], "drip")
            except BadRequest:
                await approve_join_request_db(req["user_id"], ch["chat_id"], "drip")
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except Exception as e:
                logger.error(f"Drip error: {e}")
            await asyncio.sleep(0.5)

async def auto_post_job(app: Application):
    from database.models import get_due_auto_posts, update_auto_post_next
    posts = await get_due_auto_posts()
    for post in posts:
        try:
            await app.bot.send_message(post["group_chat_id"], post.get("content", ""), parse_mode="HTML")
            await update_auto_post_next(post["schedule_id"], post["interval_minutes"])
        except Exception as e:
            logger.error(f"Auto-post error: {e}")

async def scheduled_broadcast_job(app: Application):
    from database.models import get_scheduled_broadcasts, update_broadcast_progress, get_broadcast_targets, mark_user_blocked
    from telegram.error import Forbidden
    broadcasts = await get_scheduled_broadcasts()
    for bc in broadcasts:
        targets = await get_broadcast_targets(bc["owner_id"], bc.get("target_segment", "all"), bc.get("channel_id"))
        sent = failed = blocked = 0
        for uid in targets:
            try:
                if bc.get("content_type") == "photo" and bc.get("media_file_id"):
                    await app.bot.send_photo(uid, bc["media_file_id"], caption=bc.get("caption", ""))
                else:
                    await app.bot.send_message(uid, bc.get("content", ""), parse_mode="HTML")
                sent += 1
            except Forbidden: blocked += 1; await mark_user_blocked(uid)
            except Exception: failed += 1
            if sent % 25 == 0: await asyncio.sleep(1)
        await update_broadcast_progress(bc["broadcast_id"], sent, failed, blocked, "completed")

def setup_scheduler(app: Application):
    scheduler.add_job(drip_approve_job, IntervalTrigger(minutes=5), args=[app], id="drip", replace_existing=True, max_instances=1)
    scheduler.add_job(auto_post_job, IntervalTrigger(minutes=1), args=[app], id="autopost", replace_existing=True, max_instances=1)
    scheduler.add_job(scheduled_broadcast_job, IntervalTrigger(minutes=2), args=[app], id="broadcast", replace_existing=True, max_instances=1)
    scheduler.start()
    logger.info("Scheduler started")
