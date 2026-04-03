"""Database models and queries."""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from database.connection import Database

logger = logging.getLogger(__name__)


# ─── USERS / END_USERS ───

async def ensure_user(user_id: int, username: str = None, full_name: str = None, referrer_id: int = None):
    existing = await Database.fetchrow(
        "SELECT id FROM end_users WHERE user_id = $1", user_id
    )
    if not existing:
        await Database.execute(
            "INSERT INTO end_users (user_id, username, full_name, referred_by, created_at) "
            "VALUES ($1, $2, $3, $4, NOW()) ON CONFLICT (user_id) DO NOTHING",
            user_id, username, full_name, referrer_id
        )
    else:
        await Database.execute(
            "UPDATE end_users SET username = $2, full_name = $3, last_seen = NOW() WHERE user_id = $1",
            user_id, username, full_name
        )


async def record_end_user(user_id: int, username: str = None, first_name: str = None, language_code: str = None):
    await Database.execute(
        "INSERT INTO end_users (user_id, username, full_name, language_code, created_at) "
        "VALUES ($1, $2, $3, $4, NOW()) ON CONFLICT (user_id) DO UPDATE SET "
        "username = $2, full_name = $3, last_seen = NOW()",
        user_id, username, first_name, language_code
    )


async def mark_user_blocked(user_id: int):
    await Database.execute(
        "UPDATE end_users SET is_blocked = TRUE WHERE user_id = $1", user_id
    )


async def get_referral_stats(user_id: int) -> dict:
    row = await Database.fetchrow(
        "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_blocked = FALSE) as active "
        "FROM end_users WHERE referred_by = $1", user_id
    )
    return row or {"total": 0, "active": 0}


# ─── CHANNEL OWNERS ───

async def get_owner_tier(user_id: int) -> str:
    row = await Database.fetchrow(
        "SELECT tier FROM channel_owners WHERE user_id = $1", user_id
    )
    return (row or {}).get("tier", "free")


# ─── MANAGED CHANNELS ───

async def get_owner_channels(owner_id: int) -> list:
    return await Database.fetch(
        "SELECT * FROM managed_channels WHERE owner_id = $1 AND is_active = TRUE", owner_id
    )


async def get_managed_channel(chat_id: int) -> Optional[dict]:
    return await Database.fetchrow(
        "SELECT * FROM managed_channels WHERE chat_id = $1", chat_id
    )


async def add_managed_channel(chat_id: int, chat_title: str, owner_id: int, chat_type: str = "channel"):
    await Database.execute(
        "INSERT INTO managed_channels (chat_id, chat_title, owner_id, chat_type, is_active, auto_approve, created_at) "
        "VALUES ($1, $2, $3, $4, TRUE, TRUE, NOW()) ON CONFLICT (chat_id) DO UPDATE SET "
        "chat_title = $2, owner_id = $3, is_active = TRUE",
        chat_id, chat_title, owner_id, chat_type
    )
    # Ensure owner exists in channel_owners
    await Database.execute(
        "INSERT INTO channel_owners (user_id, tier, created_at) "
        "VALUES ($1, 'free', NOW()) ON CONFLICT (user_id) DO NOTHING",
        owner_id
    )


async def update_channel_setting(chat_id: int, **kwargs):
    if not kwargs:
        return
    set_clauses = []
    values = [chat_id]
    for i, (k, v) in enumerate(kwargs.items(), start=2):
        set_clauses.append(f"{k} = ${i}")
        values.append(v)
    sql = f"UPDATE managed_channels SET {', '.join(set_clauses)} WHERE chat_id = $1"
    await Database.execute(sql, *values)


async def remove_managed_channel(chat_id: int):
    await Database.execute(
        "UPDATE managed_channels SET is_active = FALSE WHERE chat_id = $1", chat_id
    )


async def get_all_active_channels() -> list:
    return await Database.fetch("SELECT * FROM managed_channels WHERE is_active = TRUE")


async def get_drip_channels():
    return await Database.fetch("SELECT * FROM managed_channels WHERE drip_enabled = TRUE AND is_active = TRUE")

# ─── BROADCASTS ───
async def create_broadcast(owner_id: int, channel_id: int, content_type: str, content: str = "",
                           media_file_id: str = None, caption: str = None,
                           target_segment: str = "all") -> int:
    row = await Database.fetchrow(
        "INSERT INTO broadcasts (owner_id, channel_id, content_type, content, media_file_id, caption, "
        "target_segment, status, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, 'scheduled', NOW()) RETURNING id",
        owner_id, channel_id, content_type, content, media_file_id, caption, target_segment
    )
    return row["id"] if row else 0


async def get_broadcast_by_id(bc_id: int) -> Optional[dict]:
    return await Database.fetchrow("SELECT * FROM broadcasts WHERE id = $1", bc_id)


async def get_broadcasts(user_id: int, limit: int = 10) -> list:
    return await Database.fetch(
        "SELECT * FROM broadcasts WHERE owner_id = $1 ORDER BY created_at DESC LIMIT $2",
        user_id, limit
    )


async def get_broadcast_targets(owner_id: int, segment: str = "all", channel_id: int = None) -> list:
    if channel_id:
        rows = await Database.fetch(
            "SELECT DISTINCT jr.user_id FROM join_requests jr "
            "JOIN end_users eu ON jr.user_id = eu.user_id "
            "WHERE jr.chat_id = $1 AND jr.status = 'approved' AND eu.is_blocked = FALSE",
            channel_id
        )
    else:
        rows = await Database.fetch(
            "SELECT DISTINCT jr.user_id FROM join_requests jr "
            "JOIN end_users eu ON jr.user_id = eu.user_id "
            "JOIN managed_channels mc ON jr.chat_id = mc.chat_id "
            "WHERE mc.owner_id = $1 AND jr.status = 'approved' AND eu.is_blocked = FALSE",
            owner_id
        )
    return [r["user_id"] for r in rows]


async def update_broadcast_progress(bc_id: int, sent: int, failed: int, blocked: int, status: str):
    await Database.execute(
        "UPDATE broadcasts SET sent_count = $2, failed_count = $3, blocked_count = $4, status = $5 WHERE id = $1",
        bc_id, sent, failed, blocked, status
    )


# ─── JOIN REQUESTS ───

async def record_join_request(chat_id: int, user_id: int, username: str = None, first_name: str = None):
    await Database.execute(
        "INSERT INTO join_requests (chat_id, user_id, username, first_name, status, created_at) "
        "VALUES ($1, $2, $3, $4, 'pending', NOW()) ON CONFLICT (chat_id, user_id) DO UPDATE SET "
        "status = 'pending', created_at = NOW()",
        chat_id, user_id, username, first_name
    )


async def get_pending_requests(chat_id: int) -> list:
    return await Database.fetch(
        "SELECT * FROM join_requests WHERE chat_id = $1 AND status = 'pending' ORDER BY created_at DESC",
        chat_id
    )


async def approve_request(chat_id: int, user_id: int):
    await Database.execute(
        "UPDATE join_requests SET status = 'approved', approved_at = NOW() "
        "WHERE chat_id = $1 AND user_id = $2",
        chat_id, user_id
    )
    await Database.execute(
        "UPDATE managed_channels SET total_approved = total_approved + 1 WHERE chat_id = $1",
        chat_id
    )


# ─── STATS ───

async def increment_channel_stat(chat_id: int, field: str, count: int = 1):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    await Database.execute(
        f"INSERT INTO daily_stats (chat_id, date, {field}) "
        f"VALUES ($1, $2, $3) ON CONFLICT (chat_id, date) DO UPDATE SET "
        f"{field} = daily_stats.{field} + $3",
        chat_id, today, count
    )


async def get_channel_stats(chat_id: int, days: int = 7) -> list:
    return await Database.fetch(
        "SELECT * FROM daily_stats WHERE chat_id = $1 AND date >= (CURRENT_DATE - $2) "
        "ORDER BY date DESC",
        chat_id, days
    )


async def get_global_stats() -> dict:
    users = await Database.fetchrow("SELECT COUNT(*) as count FROM end_users")
    channels = await Database.fetchrow("SELECT COUNT(*) as count FROM managed_channels WHERE is_active = TRUE")
    owners = await Database.fetchrow("SELECT COUNT(*) as count FROM channel_owners")
    today_stats = await Database.fetchrow(
        "SELECT COALESCE(SUM(requests_received), 0) as requests, "
        "COALESCE(SUM(requests_approved), 0) as approved, "
        "COALESCE(SUM(dms_sent), 0) as dms "
        "FROM daily_stats WHERE date = CURRENT_DATE"
    )
    return {
        "total_users": (users or {}).get("count", 0),
        "active_channels": (channels or {}).get("count", 0),
        "total_owners": (owners or {}).get("count", 0),
        "today_requests": (today_stats or {}).get("requests", 0),
        "today_approved": (today_stats or {}).get("approved", 0),
        "today_dms": (today_stats or {}).get("dms", 0),
    }


# ─── TEMPLATES ───

async def get_templates(owner_id: int) -> list:
    return await Database.fetch(
        "SELECT * FROM templates WHERE owner_id = $1 ORDER BY created_at DESC", owner_id
    )


async def save_template(owner_id: int, name: str, content_type: str,
                        content: str = None, media_file_id: str = None, caption: str = None):
    await Database.execute(
        "INSERT INTO templates (owner_id, name, content_type, content, media_file_id, caption, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, NOW()) ON CONFLICT (owner_id, name) DO UPDATE SET "
        "content_type = $3, content = $4, media_file_id = $5, caption = $6",
        owner_id, name, content_type, content, media_file_id, caption
    )


async def delete_template(owner_id: int, name: str):
    await Database.execute(
        "DELETE FROM templates WHERE owner_id = $1 AND name = $2", owner_id, name
    )


# ─── CLONE BOTS ───

async def get_cloned_bots(owner_id: int) -> list:
    return await Database.fetch(
        "SELECT * FROM bot_clones WHERE owner_id = $1", owner_id
    )


async def create_clone_bot(owner_id: int, bot_token: str, bot_username: str, bot_name: str) -> int:
    row = await Database.fetchrow(
        "INSERT INTO bot_clones (owner_id, bot_token, bot_username, bot_name, is_active, created_at) "
        "VALUES ($1, $2, $3, $4, TRUE, NOW()) RETURNING id",
        owner_id, bot_token, bot_username, bot_name
    )
    return row["id"] if row else 0


async def delete_clone_bot(clone_id: int, owner_id: int):
    await Database.execute(
        "DELETE FROM bot_clones WHERE id = $1 AND owner_id = $2", clone_id, owner_id
    )


# ─── AUTO POSTER ───

async def get_auto_post_groups(owner_id: int) -> list:
    return await Database.fetch(
        "SELECT * FROM managed_channels WHERE owner_id = $1 AND chat_type IN ('group', 'supergroup') AND is_active = TRUE",
        owner_id
    )


async def create_auto_post_schedule(owner_id: int, group_id: int, content: str, content_type: str, interval_min: int) -> int:
    # Store as a broadcast with special status
    row = await Database.fetchrow(
        "INSERT INTO broadcasts (owner_id, channel_id, content_type, content, status, target_segment, created_at) "
        "VALUES ($1, $2, $3, $4, 'autopost', 'all', NOW()) RETURNING id",
        owner_id, group_id, content_type, content
    )
    return row["id"] if row else 0


# ─── CROSS PROMO ───

async def upsert_cross_promo(chat_id: int, owner_id: int, category: str):
    await Database.execute(
        "UPDATE managed_channels SET cross_promo_enabled = TRUE, cross_promo_category = $2 WHERE chat_id = $1",
        chat_id, category
    )


async def get_cross_promo_listings(category: str = None) -> list:
    if category:
        return await Database.fetch(
            "SELECT * FROM managed_channels WHERE cross_promo_enabled = TRUE AND cross_promo_category = $1",
            category
        )
    return await Database.fetch("SELECT * FROM managed_channels WHERE cross_promo_enabled = TRUE")


# ─── WELCOME MESSAGES ───

async def get_welcome_messages(chat_id: int) -> list:
    return await Database.fetch(
        "SELECT * FROM welcome_messages WHERE chat_id = $1 ORDER BY language_code", chat_id
    )


# ─── PLATFORM SETTINGS ───

async def get_setting(key: str, default: str = None) -> str:
    row = await Database.fetchrow(
        "SELECT value FROM platform_settings WHERE key = $1", key
    )
    return (row or {}).get("value", default)


async def set_setting(key: str, value: str):
    await Database.execute(
        "INSERT INTO platform_settings (key, value, updated_at) "
        "VALUES ($1, $2, NOW()) ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()",
        key, value
    )


async def get_all_settings() -> dict:
    rows = await Database.fetch("SELECT key, value FROM platform_settings")
    return {r["key"]: r["value"] for r in rows}


# ─── FORCE SUBSCRIBE ───

async def get_force_sub_channels(chat_id: int) -> list:
    """Get channels required for force subscription."""
    channel = await get_managed_channel(chat_id)
    if not channel:
        return []
    fs_channels = channel.get("force_sub_channels") or []
    if isinstance(fs_channels, str):
        import json
        try:
            fs_channels = json.loads(fs_channels)
        except:
            fs_channels = []
    return fs_channels


async def add_force_sub_channel(chat_id: int, target_channel: str):
    """Add a channel to force subscribe list."""
    import json
    channels = await get_force_sub_channels(chat_id)
    if target_channel not in channels:
        channels.append(target_channel)
    await update_channel_setting(chat_id, force_sub_channels=json.dumps(channels))


async def remove_force_sub_channel(chat_id: int, target_channel: str):
    """Remove a channel from force subscribe list."""
    import json
    channels = await get_force_sub_channels(chat_id)
    channels = [c for c in channels if c != target_channel]
    await update_channel_setting(chat_id, force_sub_channels=json.dumps(channels))

# ─── ADMIN FUNCTIONS ───

async def get_all_owners(limit=50):
    return await Database.fetch(
        "SELECT * FROM channel_owners ORDER BY created_at DESC LIMIT $1", limit
    )


async def ban_user(user_id: int):
    await Database.execute(
        "UPDATE channel_owners SET is_banned = TRUE WHERE user_id = $1", user_id
    )
    await Database.execute(
        "UPDATE end_users SET is_blocked = TRUE WHERE user_id = $1", user_id
    )


async def unban_user(user_id: int):
    await Database.execute(
        "UPDATE channel_owners SET is_banned = FALSE WHERE user_id = $1", user_id
    )
    await Database.execute(
        "UPDATE end_users SET is_blocked = FALSE WHERE user_id = $1", user_id
    )


async def set_user_tier(user_id: int, tier: str):
    await Database.execute(
        "INSERT INTO channel_owners (user_id, tier, created_at) "
        "VALUES ($1, $2, NOW()) ON CONFLICT (user_id) DO UPDATE SET tier = $2",
        user_id, tier
    )


async def get_all_user_ids():
    rows = await Database.fetch("SELECT DISTINCT user_id FROM end_users WHERE is_blocked = FALSE")
    return [r["user_id"] for r in rows]

# ─── MISSING FUNCTIONS (imported by other handlers) ───

async def get_channel_owner(user_id: int):
    return await Database.fetchrow("SELECT * FROM channel_owners WHERE user_id = $1", user_id)


async def register_channel_owner(user_id: int, username: str = None, full_name: str = None):
    await ensure_user(user_id, username, full_name)


async def track_interaction(user_id: int, action: str):
    try:
        await Database.execute("UPDATE channel_owners SET last_active = NOW() WHERE user_id = $1", user_id)
    except Exception:
        pass


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


async def mark_force_sub_completed(user_id: int, chat_id: int):
    await Database.execute(
        "UPDATE join_requests SET force_sub_completed = TRUE WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id
    )


async def increment_dm_count(chat_id: int):
    await increment_channel_stat(chat_id, "dms_sent")


async def update_channel_stats(chat_id: int, approved: int = 0, declined: int = 0, dms: int = 0):
    if approved > 0:
        await increment_channel_stat(chat_id, "requests_approved", approved)
    if dms > 0:
        await increment_channel_stat(chat_id, "dms_sent", dms)


async def get_scheduled_broadcasts():
    return await Database.fetch(
        "SELECT * FROM broadcasts WHERE status = 'scheduled' AND scheduled_at <= NOW()"
    )


async def get_due_auto_posts():
    return []


async def update_auto_post_next(schedule_id: int, interval: int):
    pass
