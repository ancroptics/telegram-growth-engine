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

async def get_channel_owner(user_id: int):
    return await Database.fetchrow("SELECT * FROM channel_owners WHERE user_id = $1", user_id)

async def register_channel_owner(user_id: int, username: str = None, full_name: str = None):
    await Database.execute(
        "INSERT INTO channel_owners (user_id, username, full_name) VALUES ($1, $2, $3) "
        "ON CONFLICT (user_id) DO UPDATE SET username = COALESCE($2, channel_owners.username), "
        "full_name = COALESCE($3, channel_owners.full_name), updated_at = NOW()",
        user_id, username, full_name
    )

async def get_owner_tier(user_id: int) -> str:
    row = await Database.fetchrow(
        "SELECT tier, tier_expires_at FROM channel_owners WHERE user_id = $1", user_id
    )
    if not row:
        return "free"
    tier = row.get("tier", "free")
    expires = row.get("tier_expires_at")
    if tier != "free" and expires and datetime.fromisoformat(str(expires)) < datetime.utcnow():
        await Database.execute(
            "UPDATE channel_owners SET tier = 'free' WHERE user_id = $1", user_id
        )
        return "free"
    return tier or "free"

async def set_user_tier(user_id: int, tier: str, days: int = 30):
    expires = datetime.utcnow() + timedelta(days=days) if tier != "free" else None
    await Database.execute(
        "UPDATE channel_owners SET tier = $2, tier_expires_at = $3 WHERE user_id = $1",
        user_id, tier, expires
    )

async def ban_user(user_id: int):
    await Database.execute("UPDATE channel_owners SET is_banned = true WHERE user_id = $1", user_id)

async def unban_user(user_id: int):
    await Database.execute("UPDATE channel_owners SET is_banned = false WHERE user_id = $1", user_id)

async def get_all_owners():
    return await Database.fetch("SELECT * FROM channel_owners ORDER BY created_at DESC")

async def get_all_user_ids():
    rows = await Database.fetch("SELECT user_id FROM end_users")
    return [r["user_id"] for r in rows]

async def mark_user_blocked(user_id: int):
    await Database.execute(
        "UPDATE end_users SET is_blocked = true WHERE user_id = $1", user_id
    )

async def record_end_user(chat_id: int, user_id: int, username: str = None):
    await Database.execute(
        "INSERT INTO end_users (user_id, username, channel_id, created_at) "
        "VALUES ($1, $2, $3, NOW()) ON CONFLICT (user_id) DO NOTHING",
        user_id, username, chat_id
    )


# ─── CHANNELS ───

async def add_managed_channel(chat_id: int, owner_id: int, chat_title: str = None, chat_type: str = "channel"):
    await Database.execute(
        "INSERT INTO managed_channels (chat_id, owner_id, chat_title, chat_type, created_at) "
        "VALUES ($1, $2, $3, $4, NOW()) ON CONFLICT (chat_id) DO UPDATE SET "
        "chat_title = COALESCE($3, managed_channels.chat_title), owner_id = $2",
        chat_id, owner_id, chat_title, chat_type
    )

async def remove_managed_channel(chat_id: int):
    await Database.execute("DELETE FROM managed_channels WHERE chat_id = $1", chat_id)

async def get_managed_channel(chat_id: int):
    return await Database.fetchrow("SELECT * FROM managed_channels WHERE chat_id = $1", chat_id)

async def get_owner_channels(owner_id: int):
    return await Database.fetch(
        "SELECT * FROM managed_channels WHERE owner_id = $1 ORDER BY created_at DESC", owner_id
    )

async def get_all_active_channels():
    return await Database.fetch("SELECT * FROM managed_channels WHERE is_active = true")

async def update_channel_setting(chat_id: int, key: str, value):
    import json
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    await Database.execute(
        f"UPDATE managed_channels SET {key} = $2 WHERE chat_id = $1",
        chat_id, value
    )

async def update_channel_stats(chat_id: int, **kwargs):
    sets = []
    vals = [chat_id]
    i = 2
    for k, v in kwargs.items():
        sets.append(f"{k} = ${i}")
        vals.append(v)
        i += 1
    if sets:
        await Database.execute(
            f"UPDATE managed_channels SET {', '.join(sets)} WHERE chat_id = $1", *vals
        )

async def get_channel_stats(chat_id: int):
    return await Database.fetchrow(
        "SELECT total_approved, total_declined, total_pending, member_count, "
        "dm_sent_count, dm_failed_count FROM managed_channels WHERE chat_id = $1",
        chat_id
    )

async def increment_channel_stat(chat_id: int, field: str, amount: int = 1):
    await Database.execute(
        f"UPDATE managed_channels SET {field} = COALESCE({field}, 0) + $2 WHERE chat_id = $1",
        chat_id, amount
    )

async def increment_dm_count(chat_id: int, success: bool = True):
    field = "dm_sent_count" if success else "dm_failed_count"
    await increment_channel_stat(chat_id, field, 1)


# ─── JOIN REQUESTS ───

async def record_join_request(chat_id: int, user_id: int, username: str = None, first_name: str = None):
    await Database.execute(
        "INSERT INTO join_requests (chat_id, user_id, username, first_name, status, created_at) "
        "VALUES ($1, $2, $3, $4, 'pending', NOW()) ON CONFLICT (chat_id, user_id) DO UPDATE SET "
        "status = 'pending', username = COALESCE($3, join_requests.username), updated_at = NOW()",
        chat_id, user_id, username, first_name
    )

async def approve_join_request_db(chat_id: int, user_id: int):
    await Database.execute(
        "UPDATE join_requests SET status = 'approved', approved_at = NOW() WHERE chat_id = $1 AND user_id = $2",
        chat_id, user_id
    )
    await increment_channel_stat(chat_id, "total_approved")

async def decline_join_request_db(chat_id: int, user_id: int):
    await Database.execute(
        "UPDATE join_requests SET status = 'declined', updated_at = NOW() WHERE chat_id = $1 AND user_id = $2",
        chat_id, user_id
    )
    await increment_channel_stat(chat_id, "total_declined")

async def get_pending_requests(chat_id: int, limit: int = 200):
    return await Database.fetch(
        "SELECT * FROM join_requests WHERE chat_id = $1 AND status = 'pending' ORDER BY created_at ASC LIMIT $2",
        chat_id, limit
    )

async def approve_request(chat_id: int, user_id: int):
    await approve_join_request_db(chat_id, user_id)


# ─── FORCE SUBSCRIBE ───

async def get_force_sub_channels(chat_id: int):
    return await Database.fetch(
        "SELECT * FROM force_sub_channels WHERE parent_chat_id = $1 AND is_active = true",
        chat_id
    )

async def add_force_sub_channel(parent_chat_id: int, required_chat_id: int, required_chat_title: str = None):
    await Database.execute(
        "INSERT INTO force_sub_channels (parent_chat_id, required_chat_id, required_chat_title) "
        "VALUES ($1, $2, $3) ON CONFLICT (parent_chat_id, required_chat_id) DO UPDATE SET "
        "required_chat_title = COALESCE($3, force_sub_channels.required_chat_title), is_active = true",
        parent_chat_id, required_chat_id, required_chat_title
    )

async def remove_force_sub_channel(parent_chat_id: int, required_chat_id: int):
    await Database.execute(
        "DELETE FROM force_sub_channels WHERE parent_chat_id = $1 AND required_chat_id = $2",
        parent_chat_id, required_chat_id
    )

async def mark_force_sub_completed(chat_id: int, user_id: int):
    await Database.execute(
        "UPDATE join_requests SET force_sub_completed = true WHERE chat_id = $1 AND user_id = $2",
        chat_id, user_id
    )


# ─── BROADCASTS ───

async def create_broadcast(owner_id: int, content: str = None, content_type: str = "text",
                           media_file_id: str = None, caption: str = None,
                           target_segment: str = "all", channel_id: int = None,
                           scheduled_at=None):
    return await Database.fetchval(
        "INSERT INTO broadcasts (owner_id, content, content_type, media_file_id, caption, "
        "target_segment, channel_id, scheduled_at, status, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', NOW()) RETURNING id",
        owner_id, content, content_type, media_file_id, caption,
        target_segment, channel_id, scheduled_at
    )

async def get_broadcasts(owner_id: int, limit: int = 10):
    return await Database.fetch(
        "SELECT * FROM broadcasts WHERE owner_id = $1 ORDER BY created_at DESC LIMIT $2",
        owner_id, limit
    )

async def get_broadcast_by_id(bc_id: int):
    return await Database.fetchrow("SELECT * FROM broadcasts WHERE id = $1", bc_id)

async def get_broadcast_targets(owner_id: int, segment: str = "all", channel_id: int = None):
    if channel_id:
        rows = await Database.fetch(
            "SELECT DISTINCT user_id FROM join_requests WHERE chat_id = $1 AND status = 'approved'",
            channel_id
        )
    else:
        channels = await get_owner_channels(owner_id)
        chat_ids = [c["chat_id"] for c in channels]
        if not chat_ids:
            return []
        placeholders = ", ".join(f"${i+1}" for i in range(len(chat_ids)))
        rows = await Database.fetch(
            f"SELECT DISTINCT user_id FROM join_requests WHERE chat_id IN ({placeholders}) AND status = 'approved'",
            *chat_ids
        )
    return [r["user_id"] for r in rows]

async def update_broadcast_progress(bc_id: int, sent: int, failed: int, blocked: int, status: str):
    await Database.execute(
        "UPDATE broadcasts SET sent_count = $2, failed_count = $3, blocked_count = $4, "
        "status = $5, updated_at = NOW() WHERE id = $1",
        bc_id, sent, failed, blocked, status
    )

async def get_scheduled_broadcasts():
    return await Database.fetch(
        "SELECT * FROM broadcasts WHERE status = 'scheduled' AND scheduled_at <= NOW()"
    )


# ─── REFERRALS ───

async def get_referral_stats(user_id: int):
    owner = await get_channel_owner(user_id)
    if not owner:
        return {"referral_count": 0, "referral_code": str(user_id)}
    return {
        "referral_count": owner.get("referral_count", 0),
        "referral_code": str(user_id),
    }


# ─── CLONE BOTS ───

async def get_cloned_bots(owner_id: int):
    return await Database.fetch(
        "SELECT * FROM clone_bots WHERE owner_id = $1 ORDER BY created_at DESC", owner_id
    )

async def create_clone_bot(owner_id: int, bot_token: str, bot_username: str):
    return await Database.fetchval(
        "INSERT INTO clone_bots (owner_id, bot_token, bot_username, created_at) "
        "VALUES ($1, $2, $3, NOW()) RETURNING id",
        owner_id, bot_token, bot_username
    )

async def delete_clone_bot(clone_id: int, owner_id: int):
    await Database.execute(
        "DELETE FROM clone_bots WHERE id = $1 AND owner_id = $2", clone_id, owner_id
    )


# ─── CROSS PROMO ───

async def get_cross_promo_listings(category: str = None):
    if category:
        return await Database.fetch(
            "SELECT * FROM cross_promo WHERE category = $1 AND is_active = true ORDER BY created_at DESC",
            category
        )
    return await Database.fetch(
        "SELECT * FROM cross_promo WHERE is_active = true ORDER BY created_at DESC"
    )

async def upsert_cross_promo(chat_id: int, owner_id: int, category: str, description: str = None):
    await Database.execute(
        "INSERT INTO cross_promo (chat_id, owner_id, category, description, created_at) "
        "VALUES ($1, $2, $3, $4, NOW()) ON CONFLICT (chat_id) DO UPDATE SET "
        "category = $3, description = $4, is_active = true",
        chat_id, owner_id, category, description
    )


# ─── TEMPLATES ───

async def get_templates(owner_id: int):
    return await Database.fetch(
        "SELECT * FROM templates WHERE owner_id = $1 ORDER BY created_at DESC", owner_id
    )

async def save_template(owner_id: int, name: str, content: str, template_type: str = "welcome"):
    return await Database.fetchval(
        "INSERT INTO templates (owner_id, name, content, template_type, created_at) "
        "VALUES ($1, $2, $3, $4, NOW()) RETURNING id",
        owner_id, name, content, template_type
    )

async def delete_template(template_id: int, owner_id: int):
    await Database.execute(
        "DELETE FROM templates WHERE id = $1 AND owner_id = $2", template_id, owner_id
    )


# ─── AUTO POSTER ───

async def get_auto_post_groups(owner_id: int):
    return await Database.fetch(
        "SELECT * FROM auto_post_schedules WHERE owner_id = $1 ORDER BY created_at DESC",
        owner_id
    )

async def create_auto_post_schedule(owner_id: int, chat_id: int, content: str,
                                     interval_hours: int = 24, content_type: str = "text"):
    return await Database.fetchval(
        "INSERT INTO auto_post_schedules (owner_id, chat_id, content, interval_hours, "
        "content_type, next_post_at, created_at) VALUES ($1, $2, $3, $4, $5, NOW(), NOW()) RETURNING id",
        owner_id, chat_id, content, interval_hours, content_type
    )

async def get_due_auto_posts():
    return await Database.fetch(
        "SELECT * FROM auto_post_schedules WHERE is_active = true AND next_post_at <= NOW()"
    )

async def update_auto_post_next(schedule_id: int):
    await Database.execute(
        "UPDATE auto_post_schedules SET next_post_at = NOW() + (interval_hours || ' hours')::interval, "
        "last_posted_at = NOW() WHERE id = $1",
        schedule_id
    )


# ─── WELCOME MESSAGES ───

async def get_welcome_messages(chat_id: int):
    channel = await get_managed_channel(chat_id)
    if not channel:
        return {}
    import json
    i18n = channel.get("welcome_messages_i18n") or "{}"
    if isinstance(i18n, str):
        i18n = json.loads(i18n)
    return i18n


# ─── DRIP ───

async def get_drip_channels():
    return await Database.fetch(
        "SELECT * FROM managed_channels WHERE drip_enabled = true AND is_active = true"
    )


# ─── PLATFORM SETTINGS ───

async def get_all_settings():
    rows = await Database.fetch("SELECT * FROM platform_settings ORDER BY key")
    return {r["key"]: r["value"] for r in rows}

async def get_setting(key: str, default=None):
    row = await Database.fetchrow("SELECT value FROM platform_settings WHERE key = $1", key)
    return row["value"] if row else default

async def set_setting(key: str, value: str):
    await Database.execute(
        "INSERT INTO platform_settings (key, value, updated_at) VALUES ($1, $2, NOW()) "
        "ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()",
        key, value
    )


# ─── GLOBAL STATS ───

async def get_global_stats():
    owners = await Database.fetchval("SELECT COUNT(*) FROM channel_owners") or 0
    channels = await Database.fetchval("SELECT COUNT(*) FROM managed_channels WHERE is_active = true") or 0
    users = await Database.fetchval("SELECT COUNT(*) FROM end_users") or 0
    pending = await Database.fetchval("SELECT COUNT(*) FROM join_requests WHERE status = 'pending'") or 0
    approved_today = await Database.fetchval(
        "SELECT COUNT(*) FROM join_requests WHERE status = 'approved' AND approved_at >= CURRENT_DATE"
    ) or 0
    return {
        "total_owners": owners,
        "total_channels": channels,
        "total_users": users,
        "total_pending": pending,
        "approved_today": approved_today,
    }


# ─── TRACKING ───

async def track_interaction(user_id: int, action: str, details: str = None):
    await Database.execute(
        "INSERT INTO interactions (user_id, action, details, created_at) "
        "VALUES ($1, $2, $3, NOW())",
        user_id, action, details
    )
