"""APScheduler setup for periodic tasks."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler = None


def setup_scheduler(app):
    """Set up periodic jobs."""
    global _scheduler
    _scheduler = AsyncIOScheduler()

    async def run_auto_posts():
        try:
            from database.models import get_due_auto_posts, update_auto_post_next
            posts = await get_due_auto_posts()
            for post in posts:
                try:
                    chat_id = post.get("group_chat_id")
                    content = post.get("content", "")
                    content_type = post.get("content_type", "text")
                    if content_type == "text" and content:
                        await app.bot.send_message(chat_id, content, parse_mode="HTML")
                    interval = post.get("interval_minutes", 60)
                    await update_auto_post_next(post["schedule_id"], interval)
                    logger.info(f"Auto-posted to {chat_id}")
                except Exception as e:
                    logger.error(f"Auto-post error for {post.get('schedule_id')}: {e}")
        except Exception as e:
            logger.error(f"Auto-post scheduler error: {e}")

    async def run_scheduled_broadcasts():
        try:
            from database.models import get_scheduled_broadcasts
            broadcasts = await get_scheduled_broadcasts()
            for bc in broadcasts:
                logger.info(f"Scheduled broadcast {bc.get('broadcast_id')} is due")
        except Exception as e:
            logger.error(f"Broadcast scheduler error: {e}")

    async def run_drip_approvals():
        try:
            from database.models import get_drip_channels, get_pending_requests, approve_join_request_db
            channels = await get_drip_channels()
            for ch in channels:
                try:
                    pending = await get_pending_requests(ch["chat_id"])
                    drip_rate = ch.get("drip_rate", 1)
                    to_approve = pending[:drip_rate]
                    for req in to_approve:
                        try:
                            await app.bot.approve_chat_join_request(ch["chat_id"], req["user_id"])
                            await approve_join_request_db(req["user_id"], ch["chat_id"], method="drip")
                            logger.info(f"Drip approved {req['user_id']} for {ch['chat_id']}")
                        except Exception as e:
                            logger.error(f"Drip approve error: {e}")
                except Exception as e:
                    logger.error(f"Drip channel error: {e}")
        except Exception as e:
            logger.error(f"Drip scheduler error: {e}")

    _scheduler.add_job(run_auto_posts, IntervalTrigger(minutes=1), id="auto_posts", replace_existing=True)
    _scheduler.add_job(run_scheduled_broadcasts, IntervalTrigger(minutes=2), id="scheduled_broadcasts", replace_existing=True)
    _scheduler.add_job(run_drip_approvals, IntervalTrigger(minutes=5), id="drip_approvals", replace_existing=True)
    _scheduler.start()
    logger.info("Scheduler started with 3 jobs")
