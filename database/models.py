"""All database queries as async functions."""
import json
import logging
from datetime import datetime, timedelta
from database.connection import Database

logger = logging.getLogger(__name__)

# ─── USER / OWNER ───
async def ensure_user(user_id: int, username: str = None, full_name: str = None, referrer_id: int = None):
    existing = await Database.fetchrow("SELECT user_id FROM channel_owners WHERE user_id = $1", user_id)
    if existing:
        await Database.execute(
            "UPDATE channel_owners SET username = COALESCE($2, username), full_name = COALESCE($3, full_name), updated_at = NOW() WHERE user_id = $1",
            user_id, username, full_name
        )
        return
    await Database.execute(
        "INSERT INTO channel_owners (user_id, username, full_name, referrer_id) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
        user_id, username, full_name, referrer_id
    )
    if referrer_id:
        await Database.execute(
            "UPDATE channel_owners SET referral_count = referral_count + 1 WHERE user_id = $1", referrer_id
        )

async def get_channel_owner(user_id: int):
    return await Database.fetchrow("SELECT * FROM channel_owners WHERE user_id = $1", user_id)

async def register_channel_owner(user_id: int, username: str = None, full_name: str = None):
    await ensure_user(user_id, username, full_name)

async def get_owner_tier(user_id: int) -> str:
    row = await Database.fetchrow("SELECT tier, tier_expires_at FROM channel_owners WHERE user_id = $1", user_id)
    if not row: return "free"
    if row["tier"] != "free" and row["tier_expires_at"] and row["tier_expires_at"] < datetime.now():
        await Database.execute("UPDATE channel_owners SET tier = 'free', tier_expires_at = NULL WHERE user_id = $1", user_id)
        return "free"
    return row["tier"] or "free"

async def set_user_tier(user_id: int, tier: str, days: int = 30):
    expires = datetime.now() + timedelta(days=days) if tier != "free" else None
    await Database.execute(
        "UPDATE channel_owners SET tier = $2, tier_expires_at = $3, updated_at = NOW() WHERE user_id = $1",
        user_id, tier, expires
    )

async def get_referral_stats(user_id: int) -> dict:
    row = await Database.fetchrow("SELECT referral_count FROM channel_owners WHERE user_id = $1", user_id)
    total = row["referral_count"] if row else 0
    active = await Database.fetchval(
        "SELECT COUNT(*) FROM channel_owners co JOIN managed_channels mc ON co.user_id = mc.owner_id WHERE co.referrer_id = $1",
        user_id
    )
    return {"total": total, "active": active or 0}

async def ban_user(user_id: int):
    await Database.execute("UPDATE channel_owners SET is_banned = TRUE WHERE user_id = $1", user_id)

async def unban_user(user_id: int):
    await Database.execute("UPDATE channel_owners SET is_banned = FALSE WHERE user_id = $1", user_id)

async def mark_user_blocked(user_id: int):
    await Database.execute("UPDATE channel_owners SET is_blocked = TRUE WHERE user_id = $1", user_id)

async def track_interaction(user_id: int, action: str):
    await Database.execute("INSERT INTO interactions (user_id, action) VALUES ($1, $2)", user_id, action)

# ─── CHANNELS ───
async def add_managed_channel(chat_id: int, chat_title: str, chat_type: str, chat_username: str, owner_id: int, member_count: int = 0):
    await Database.execute(
        """INSERT INTO managed_channels (chat_id, chat_title, chat_type, chat_username, owner_id, member_count)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT (chat_id) DO UPDATE SET chat_title = $2, chat_username = $4, member_count = $6, updated_at = NOW()""",
        chat_id, chat_title, chat_type, chat_username, owner_id, member_count
    )

async def remove_managed_channel(chat_id: int):
    await Database.execute("DELETE FROM managed_channels WHERE chat_id = $1", chat_id)

async def get_managed_channel(chat_id: int):
    return await Database.fetchrow("SELECT * FROM managed_channels WHERE chat_id = $1", chat_id)

async def get_owner_channels(owner_id: int):
    return await Database.fetch("SELECT * FROM managed_channels WHERE owner_id = $1 ORDER BY created_at", owner_id)

async def update_channel_setting(chat_id: int, **kwargs):
    if not kwargs: return
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys()))
    vals = [chat_id] + list(kwargs.values())
    await Database.execute(f"UPDATE managed_channels SET {sets}, updated_at = NOW() WHERE chat_id = $1", *vals)

async def update_channel_stats(chat_id: int, approved: int = 0, declined: int = 0, dms: int = 0):
    await Database.execute(
        """INSERT INTO channel_stats (chat_id, date, requests_approved, requests_declined, dms_sent)
           VALUES ($1, CURRENT_DATE, $2, $3, $4)
           ON CONFLICT (chat_id, date) DO UPDATE SET
           requests_approved = channel_stats.requests_approved + $2,
           requests_declined = channel_stats.requests_declined + $3,
           dms_sent = channel_stats.dms_sent + $4""",
        chat_id, approved, declined, dms
    )
    if approved > 0:
        await Database.execute("UPDATE managed_channels SET total_approved = total_approved + $2 WHERE chat_id = $1", chat_id, approved)

async def increment_dm_count(chat_id: int):
    await Database.execute("UPDATE managed_channels SET total_dms_sent = total_dms_sent + 1 WHERE chat_id = $1", chat_id)
    await update_channel_stats(chat_id, dms=1)

async def get_channel_stats(chat_id: int, days: int = 7):
    return await Database.fetch(
        "SELECT * FROM channel_stats WHERE chat_id = $1 AND date >= CURRENT_DATE - $2 ORDER BY date DESC",
        chat_id, days
    )

# ─── JOIN REQUESTS ───
async def record_join_request(user_id: int, chat_id: int, full_name: str = None, username: str = None):
    await Database.execute(
        """INSERT INTO join_requests (user_id, chat_id, user_full_name, user_username)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (user_id, chat_id) DO UPDATE SET status = 'pending', user_full_name = $3, user_username = $4, created_at = NOW()""",
        user_id, chat_id, full_name, username
    )
    await Database.execute(
        """INSERT INTO channel_stats (chat_id, date, requests_received) VALUES ($1, CURRENT_DATE, 1)
           ON CONFLICT (chat_id, date) DO UPDATE SET requests_received = channel_stats.requests_received + 1""",
        chat_id
    )

async def approve_join_request_db(user_id: int, chat_id: int, method: str = "auto"):
    await Database.execute(
        "UPDATE join_requests SET status = 'approved', approved_via = $3, processed_at = NOW() WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id, method
    )

async def decline_join_request_db(user_id: int, chat_id: int):
    await Database.execute(
        "UPDATE join_requests SET status = 'declined', processed_at = NOW() WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id
    )

async def get_pending_requests(chat_id: int, limit: int = 100):
    return await Database.fetch(
        "SELECT * FROM join_requests WHERE chat_id = $1 AND status = 'pending' ORDER BY created_at LIMIT $2",
        chat_id, limit
    )

async def mark_force_sub_completed(user_id: int, chat_id: int):
    await Database.execute(
        "UPDATE join_requests SET force_sub_completed = TRUE WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id
    )

async def get_drip_channels():
    return await Database.fetch("SELECT * FROM managed_channels WHERE drip_enabled = TRUE")

# ─── BROADCASTS ───
async def create_broadcast(owner_id, channel_id, content_type, content, media_file_id=None, caption=None, target_segment="all", scheduled_at=None):
    return await Database.fetchval(
        """INSERT INTO broadcasts (owner_id, channel_id, content_type, content, media_file_id, caption, target_segment, status, scheduled_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING broadcast_id""",
        owner_id, channel_id, content_type, content, media_file_id, caption, target_segment,
        "scheduled" if scheduled_at else "draft", scheduled_at
    )

async def get_broadcasts(owner_id: int, limit: int = 10):
    return await Database.fetch(
        "SELECT * FROM broadcasts WHERE owner_id = $1 ORDER BY created_at DESC LIMIT $2", owner_id, limit
    )

async def get_broadcast_by_id(bc_id: int):
    return await Database.fetchrow("SELECT * FROM broadcasts WHERE broadcast_id = $1", bc_id)

async def get_broadcast_targets(owner_id: int, segment: str, channel_id: int = None):
    if channel_id:
        rows = await Database.fetch(
            "SELECT DISTINCT user_id FROM join_requests WHERE chat_id = $1 AND status = 'approved'", channel_id
        )
    else:
        channels = await get_owner_channels(owner_id)
        chat_ids = [c["chat_id"] for c in channels]
        if not chat_ids: return []
        placeholders = ", ".join(f"${i+1}" for i in range(len(chat_ids)))
        rows = await Database.fetch(
            f"SELECT DISTINCT user_id FROM join_requests WHERE chat_id IN ({placeholders}) AND status = 'approved'",
            *chat_ids
        )
    return [r["user_id"] for r in rows]

async def update_broadcast_progress(bc_id, sent, failed, blocked, status):
    await Database.execute(
        "UPDATE broadcasts SET sent_count=$2, failed_count=$3, blocked_count=$4, status=$5, completed_at=CASE WHEN $5='completed' THEN NOW() ELSE completed_at END WHERE broadcast_id=$1",
        bc_id, sent, failed, blocked, status
    )

async def get_scheduled_broadcasts():
    return await Database.fetch(
        "SELECT * FROM broadcasts WHERE status = 'scheduled' AND scheduled_at <= NOW()"
    )

# ─── TEMPLATES ───
async def get_templates(owner_id: int):
    return await Database.fetch("SELECT * FROM templates WHERE owner_id = $1 ORDER BY name", owner_id)

async def save_template(owner_id, name, content_type, content=None, media_file_id=None, caption=None):
    await Database.execute(
        """INSERT INTO templates (owner_id, name, content_type, content, media_file_id, caption)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT (owner_id, name) DO UPDATE SET content_type=$3, content=$4, media_file_id=$5, caption=$6""",
        owner_id, name, content_type, content, media_file_id, caption
    )

async def delete_template(owner_id: int, name: str):
    await Database.execute("DELETE FROM templates WHERE owner_id = $1 AND name = $2", owner_id, name)

# ─── AUTO POSTER ───
async def get_auto_post_groups(owner_id: int):
    return await Database.fetch("SELECT * FROM auto_post_groups WHERE owner_id = $1", owner_id)

async def create_auto_post_schedule(owner_id, group_id, content, content_type, interval):
    return await Database.fetchval(
        "INSERT INTO auto_post_schedules (owner_id, group_chat_id, content, content_type, interval_minutes) VALUES ($1,$2,$3,$4,$5) RETURNING schedule_id",
        owner_id, group_id, content, content_type, interval
    )

async def get_due_auto_posts():
    return await Database.fetch("SELECT * FROM auto_post_schedules WHERE is_active = TRUE AND next_run_at <= NOW()")

async def update_auto_post_next(schedule_id: int, interval: int):
    await Database.execute(
        "UPDATE auto_post_schedules SET next_run_at = NOW() + ($2 || ' minutes')::INTERVAL WHERE schedule_id = $1",
        schedule_id, str(interval)
    )

# ─── CLONED BOTS ───
async def get_cloned_bots(owner_id: int):
    return await Database.fetch("SELECT * FROM cloned_bots WHERE owner_id = $1", owner_id)

async def create_clone_bot(owner_id, token, username, name):
    return await Database.fetchval(
        "INSERT INTO cloned_bots (owner_id, bot_token, bot_username, bot_name) VALUES ($1,$2,$3,$4) RETURNING id",
        owner_id, token, username, name
    )

async def delete_clone_bot(clone_id: int, owner_id: int):
    await Database.execute("DELETE FROM cloned_bots WHERE id = $1 AND owner_id = $2", clone_id, owner_id)

# ─── GLOBAL STATS ───
async def get_global_stats():
    users = await Database.fetchval("SELECT COUNT(*) FROM channel_owners")
    channels = await Database.fetchval("SELECT COUNT(*) FROM managed_channels")
    approved = await Database.fetchval("SELECT COALESCE(SUM(total_approved), 0) FROM managed_channels")
    dms = await Database.fetchval("SELECT COALESCE(SUM(total_dms_sent), 0) FROM managed_channels")
    premium = await Database.fetchval("SELECT COUNT(*) FROM channel_owners WHERE tier = 'premium'")
    business = await Database.fetchval("SELECT COUNT(*) FROM channel_owners WHERE tier = 'business'")
    return {"total_users": users, "total_channels": channels, "total_approved": approved, "total_dms": dms, "premium_users": premium, "business_users": business}

async def get_all_owners(limit=20):
    return await Database.fetch(
        """SELECT co.*, COUNT(mc.chat_id) as channel_count FROM channel_owners co
           LEFT JOIN managed_channels mc ON co.user_id = mc.owner_id
           GROUP BY co.user_id ORDER BY channel_count DESC LIMIT $1""", limit
    )

async def get_all_user_ids():
    rows = await Database.fetch("SELECT user_id FROM channel_owners WHERE is_banned = FALSE AND is_blocked = FALSE")
    return [r["user_id"] for r in rows]

# ─── CROSS PROMO ───
async def get_cross_promo_listings(category=None, exclude_owner=None):
    if category:
        return await Database.fetch(
            "SELECT cl.*, mc.chat_title, mc.chat_username FROM cross_promo_listings cl JOIN managed_channels mc ON cl.chat_id = mc.chat_id WHERE cl.is_active = TRUE AND cl.category = $1 AND cl.owner_id != COALESCE($2, 0)",
            category, exclude_owner or 0
        )
    return await Database.fetch(
        "SELECT cl.*, mc.chat_title, mc.chat_username FROM cross_promo_listings cl JOIN managed_channels mc ON cl.chat_id = mc.chat_id WHERE cl.is_active = TRUE AND cl.owner_id != COALESCE($1, 0)",
        exclude_owner or 0
    )

async def upsert_cross_promo(chat_id, owner_id, category, description=None):
    member_count = await Database.fetchval("SELECT member_count FROM managed_channels WHERE chat_id = $1", chat_id)
    await Database.execute(
        """INSERT INTO cross_promo_listings (chat_id, owner_id, category, description, member_count)
           VALUES ($1, $2, $3, $4, $5)
           ON CONFLICT (id) DO UPDATE SET category=$3, description=$4, member_count=$5, is_active=TRUE""",
        chat_id, owner_id, category, description, member_count or 0
    )
