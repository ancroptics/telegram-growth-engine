"""All database queries as async functions."""
import json
import logging
from datetime import datetime, timedelta
from database.connection import Database

logger = logging.getLogger(__name__)

# --- USER / OWNER ---
async def ensure_user(user_id: int, username: str = None, full_name: str = None, referrer_id: int = None):
    first_name = (full_name or "").split()[0] if full_name else None
    last_name = " ".join((full_name or "").split()[1:]) if full_name and " " in full_name else None
    existing = await Database.fetchrow("SELECT user_id FROM channel_owners WHERE user_id = $1", user_id)
    if existing:
        await Database.execute(
            "UPDATE channel_owners SET username = COALESCE($2, username), first_name = COALESCE($3, first_name), last_name = COALESCE($4, last_name), last_active = NOW() WHERE user_id = $1",
            user_id, username, first_name, last_name
        )
        return
    await Database.execute(
        "INSERT INTO channel_owners (user_id, username, first_name, last_name, referred_by) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
        user_id, username, first_name, last_name, referrer_id
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
    if row.get("tier") not in (None, "free") and row.get("tier_expires_at"):
        try:
            expires = row["tier_expires_at"]
            if isinstance(expires, str):
                from datetime import datetime as dt
                expires = dt.fromisoformat(expires.replace("Z", "+00:00"))
            if expires < datetime.now(expires.tzinfo if hasattr(expires, 'tzinfo') and expires.tzinfo else None):
                await Database.execute("UPDATE channel_owners SET tier = 'free', tier_expires_at = NULL WHERE user_id = $1", user_id)
                return "free"
        except Exception:
            pass
    return row.get("tier") or "free"

async def set_user_tier(user_id: int, tier: str, days: int = 30):
    expires = (datetime.now() + timedelta(days=days)).isoformat() if tier != "free" else None
    await Database.execute(
        "UPDATE channel_owners SET tier = $2, tier_expires_at = $3, last_active = NOW() WHERE user_id = $1",
        user_id, tier, expires
    )

async def get_referral_stats(user_id: int) -> dict:
    row = await Database.fetchrow("SELECT referral_count FROM channel_owners WHERE user_id = $1", user_id)
    total = row.get("referral_count", 0) if row else 0
    active = await Database.fetchval(
        "SELECT COUNT(*) FROM channel_owners co JOIN managed_channels mc ON co.user_id = mc.owner_id WHERE co.referred_by = $1",
        user_id
    )
    return {"total": total, "active": active or 0}

async def ban_user(user_id: int):
    await Database.execute("UPDATE channel_owners SET is_banned = TRUE WHERE user_id = $1", user_id)

async def unban_user(user_id: int):
    await Database.execute("UPDATE channel_owners SET is_banned = FALSE WHERE user_id = $1", user_id)

async def mark_user_blocked(user_id: int):
    await Database.execute("UPDATE end_users SET has_blocked_bot = TRUE WHERE user_id = $1", user_id)

async def track_interaction(user_id: int, action: str):
    try:
        await Database.execute("UPDATE channel_owners SET last_active = NOW() WHERE user_id = $1", user_id)
    except Exception:
        pass

# --- CHANNELS ---
async def add_managed_channel(chat_id: int, chat_title: str, chat_type: str, chat_username: str, owner_id: int, member_count: int = 0):
    await Database.execute(
        """INSERT INTO managed_channels (chat_id, chat_title, chat_type, chat_username, owner_id, member_count, bot_is_admin, is_active)
           VALUES ($1, $2, $3, $4, $5, $6, TRUE, TRUE)
           ON CONFLICT (chat_id) DO UPDATE SET chat_title = $2, chat_username = $4, member_count = $6, bot_is_admin = TRUE, is_active = TRUE""",
        chat_id, chat_title, chat_type, chat_username, owner_id, member_count
    )

async def remove_managed_channel(chat_id: int):
    await Database.execute("UPDATE managed_channels SET is_active = FALSE, bot_is_admin = FALSE WHERE chat_id = $1", chat_id)

async def get_managed_channel(chat_id: int):
    return await Database.fetchrow("SELECT * FROM managed_channels WHERE chat_id = $1", chat_id)

async def get_owner_channels(owner_id: int):
    return await Database.fetch("SELECT * FROM managed_channels WHERE owner_id = $1 AND is_active = TRUE ORDER BY added_at", owner_id)

async def update_channel_setting(chat_id: int, **kwargs):
    if not kwargs: return
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys()))
    vals = [chat_id] + list(kwargs.values())
    await Database.execute(f"UPDATE managed_channels SET {sets} WHERE chat_id = $1", *vals)

async def update_channel_stats(chat_id: int, approved: int = 0, declined: int = 0, dms: int = 0):
    await Database.execute(
        """INSERT INTO daily_stats (date, channel_id, requests_approved, dms_sent)
           VALUES (CURRENT_DATE, $1, $2, $3)
           ON CONFLICT (channel_id, date) DO UPDATE SET
           requests_approved = daily_stats.requests_approved + $2,
           dms_sent = daily_stats.dms_sent + $3""",
        chat_id, approved, dms
    )
    if approved > 0:
        await Database.execute("UPDATE managed_channels SET total_approved = total_approved + $2 WHERE chat_id = $1", chat_id, approved)

async def increment_dm_count(chat_id: int):
    await Database.execute("UPDATE managed_channels SET total_dms_sent = total_dms_sent + 1 WHERE chat_id = $1", chat_id)
    await update_channel_stats(chat_id, dms=1)

async def get_channel_stats(chat_id: int, days: int = 7):
    return await Database.fetch(
        "SELECT * FROM daily_stats WHERE channel_id = $1 AND date >= CURRENT_DATE - $2 ORDER BY date DESC",
        chat_id, days
    )

# --- JOIN REQUESTS ---
async def record_join_request(user_id: int, chat_id: int, full_name: str = None, username: str = None):
    first_name = (full_name or "").split()[0] if full_name else None
    await Database.execute(
        """INSERT INTO join_requests (user_id, chat_id, first_name, username, status)
           VALUES ($1, $2, $3, $4, 'pending')
           ON CONFLICT (user_id, chat_id) DO UPDATE SET status = 'pending', first_name = COALESCE($3, join_requests.first_name), username = COALESCE($4, join_requests.username), request_time = NOW()""",
        user_id, chat_id, first_name, username
    )
    await Database.execute(
        """INSERT INTO daily_stats (date, channel_id, requests_received) VALUES (CURRENT_DATE, $1, 1)
           ON CONFLICT (channel_id, date) DO UPDATE SET requests_received = daily_stats.requests_received + 1""",
        chat_id
    )
    await Database.execute(
        """INSERT INTO end_users (user_id, username, first_name, source, source_channel)
           VALUES ($1, $2, $3, 'join_request', $4)
           ON CONFLICT (user_id) DO UPDATE SET last_active = NOW(), username = COALESCE($2, end_users.username)""",
        user_id, username, first_name, chat_id
    )

async def approve_join_request_db(user_id: int, chat_id: int, method: str = "auto"):
    await Database.execute(
        "UPDATE join_requests SET status = 'approved', processed_by = $3, processed_at = NOW() WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id, method
    )

async def decline_join_request_db(user_id: int, chat_id: int):
    await Database.execute(
        "UPDATE join_requests SET status = 'declined', processed_at = NOW() WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id
    )

async def get_pending_requests(chat_id: int, limit: int = 100):
    return await Database.fetch(
        "SELECT * FROM join_requests WHERE chat_id = $1 AND status = 'pending' ORDER BY request_time LIMIT $2",
        chat_id, limit
    )

async def mark_force_sub_completed(user_id: int, chat_id: int):
    await Database.execute(
        "UPDATE join_requests SET force_sub_completed = TRUE WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id
    )

async def get_drip_channels():
    return await Database.fetch("SELECT * FROM managed_channels WHERE approve_mode = 'drip' AND is_active = TRUE")

# --- BROADCASTS ---
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

# --- TEMPLATES ---
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

# --- AUTO POSTER (stub) ---
async def get_auto_post_groups(owner_id: int):
    return []

async def create_auto_post_schedule(owner_id, group_id, content, content_type, interval):
    return None

async def get_due_auto_posts():
    return []

async def update_auto_post_next(schedule_id: int, interval: int):
    pass

# --- CLONED BOTS ---
async def get_cloned_bots(owner_id: int):
    return await Database.fetch("SELECT * FROM bot_clones WHERE owner_id = $1", owner_id)

async def create_clone_bot(owner_id, token, username, name):
    return await Database.fetchval(
        "INSERT INTO bot_clones (owner_id, bot_token, bot_username, bot_first_name) VALUES ($1,$2,$3,$4) RETURNING clone_id",
        owner_id, token, username, name
    )

async def delete_clone_bot(clone_id: int, owner_id: int):
    await Database.execute("DELETE FROM bot_clones WHERE clone_id = $1 AND owner_id = $2", clone_id, owner_id)

# --- GLOBAL STATS ---
async def get_global_stats():
    users = await Database.fetchval("SELECT COUNT(*) FROM channel_owners")
    channels = await Database.fetchval("SELECT COUNT(*) FROM managed_channels WHERE is_active = TRUE")
    approved = await Database.fetchval("SELECT COALESCE(SUM(total_approved), 0) FROM managed_channels")
    dms = await Database.fetchval("SELECT COALESCE(SUM(total_dms_sent), 0) FROM managed_channels")
    premium = await Database.fetchval("SELECT COUNT(*) FROM channel_owners WHERE tier = 'premium'")
    business = await Database.fetchval("SELECT COUNT(*) FROM channel_owners WHERE tier = 'business'")
    return {"total_users": users, "total_channels": channels, "total_approved": approved, "total_dms": dms, "premium_users": premium, "business_users": business}

async def get_all_owners(limit=20):
    return await Database.fetch(
        """SELECT co.*, COUNT(mc.chat_id) as channel_count FROM channel_owners co
           LEFT JOIN managed_channels mc ON co.user_id = mc.owner_id AND mc.is_active = TRUE
           GROUP BY co.user_id ORDER BY channel_count DESC LIMIT $1""", limit
    )

async def get_all_user_ids():
    rows = await Database.fetch("SELECT user_id FROM channel_owners WHERE is_banned = FALSE")
    return [r["user_id"] for r in rows]

# --- CROSS PROMO ---
async def get_cross_promo_listings(category=None, exclude_owner=None):
    if category:
        return await Database.fetch(
            "SELECT * FROM managed_channels WHERE is_active = TRUE AND cross_promo_enabled = TRUE AND cross_promo_category = $1 AND owner_id != COALESCE($2, 0)",
            category, exclude_owner or 0
        )
    return await Database.fetch(
        "SELECT * FROM managed_channels WHERE is_active = TRUE AND cross_promo_enabled = TRUE AND owner_id != COALESCE($1, 0)",
        exclude_owner or 0
    )

async def upsert_cross_promo(chat_id, owner_id, category, description=None):
    await Database.execute(
        "UPDATE managed_channels SET cross_promo_enabled = TRUE, cross_promo_category = $2, cross_promo_text = $3 WHERE chat_id = $1",
        chat_id, category, description
    )
