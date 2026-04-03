"""Database models — async helpers for Supabase REST API.
Maps to the ACTUAL database schema.
"""
import logging
from typing import Optional
from database.connection import table_select, table_insert, table_update, table_delete, table_count

logger = logging.getLogger(__name__)


# ═══ CHANNEL OWNERS ═══
async def get_or_create_owner(user_id: int, username: str = None, first_name: str = None):
    try:
        existing = await table_select("channel_owners", filters={"user_id": user_id}, single=True)
        if existing:
            return existing
        data = {"user_id": user_id, "username": username or "", "first_name": first_name or "", "tier": "free"}
        result = await table_insert("channel_owners", data, upsert=True)
        return result[0] if isinstance(result, list) and result else data
    except Exception as e:
        logger.error(f"get_or_create_owner failed: {e}")
        return {"user_id": user_id, "username": username or "", "first_name": first_name or "", "tier": "free"}

async def get_owner(user_id: int) -> Optional[dict]:
    return await table_select("channel_owners", filters={"user_id": user_id}, single=True)

async def get_owner_tier(user_id: int) -> str:
    owner = await get_owner(user_id)
    return owner.get("tier", "free") if owner else "free"

async def ban_user(user_id: int):
    await table_update("channel_owners", {"is_banned": True}, {"user_id": user_id})

async def unban_user(user_id: int):
    await table_update("channel_owners", {"is_banned": False}, {"user_id": user_id})

async def set_user_tier(user_id: int, tier: str):
    await table_update("channel_owners", {"tier": tier}, {"user_id": user_id})

async def get_all_owners() -> list:
    return await table_select("channel_owners") or []

async def get_all_user_ids() -> list:
    rows = await table_select("end_users", columns="user_id")
    return [r["user_id"] for r in (rows or [])]


# ═══ MANAGED CHANNELS ═══
async def add_managed_channel(owner_id: int, chat_id: int, chat_title: str, chat_type: str = "channel"):
    return await table_insert("managed_channels", {
        "owner_id": owner_id, "chat_id": chat_id,
        "chat_title": chat_title, "chat_type": chat_type,
        "auto_approve": False,
    }, upsert=True)

async def get_managed_channel(chat_id: int) -> Optional[dict]:
    return await table_select("managed_channels", filters={"chat_id": chat_id}, single=True)

async def get_owner_channels(owner_id: int) -> list:
    return await table_select("managed_channels", filters={"owner_id": owner_id}) or []

async def update_channel_setting(chat_id: int, key: str, value):
    await table_update("managed_channels", {key: value}, {"chat_id": chat_id})

async def delete_managed_channel(chat_id: int):
    await table_delete("managed_channels", {"chat_id": chat_id})

async def remove_managed_channel(chat_id: int):
    """Alias for delete_managed_channel."""
    await delete_managed_channel(chat_id)


# ═══ END USERS ═══
async def get_or_create_end_user(user_id: int, username: str = None, first_name: str = None,
                                  language_code: str = None, source_channel: int = None, **kwargs):
    try:
        existing = await table_select("end_users", filters={"user_id": user_id}, single=True)
        if existing:
            return existing
        data = {
            "user_id": user_id, "username": username or "", "first_name": first_name or "",
            "language_code": language_code or "en", "source_channel": source_channel,
        }
        result = await table_insert("end_users", data, upsert=True)
        return result[0] if isinstance(result, list) and result else data
    except Exception as e:
        logger.error(f"get_or_create_end_user failed: {e}")
        return {"user_id": user_id}

async def mark_user_blocked(user_id: int):
    """Mark user as having blocked the bot."""
    await table_update("end_users", {"has_blocked_bot": True}, {"user_id": user_id})


# ═══ JOIN REQUESTS ═══
async def log_join_request(user_id: int, chat_id: int, username: str = None, first_name: str = None, language: str = None, **kwargs):
    """Log a new join request."""
    return await table_insert("join_requests", {
        "user_id": user_id, "chat_id": chat_id,
        "username": username or "", "first_name": first_name or "",
        "user_language": language or "en",
        "status": "pending",
    })

async def record_join_request(user_id: int, chat_id: int, username: str = None, first_name: str = None):
    return await log_join_request(user_id, chat_id, username, first_name)

async def approve_join_request_db(request_id: int = None, user_id: int = None, chat_id: int = None, **kwargs):
    """Mark join request as approved."""
    if request_id:
        await table_update("join_requests", {"status": "approved", "processed_at": "now()"}, {"id": request_id})
    elif user_id and chat_id:
        await table_update("join_requests", {"status": "approved"}, {"user_id": user_id, "chat_id": chat_id, "status": "pending"})

async def get_pending_requests(chat_id: int, limit: int = 50) -> list:
    return await table_select("join_requests", filters={"chat_id": chat_id, "status": "pending"}, limit=limit) or []

async def update_join_request(request_id: int, **kwargs):
    await table_update("join_requests", kwargs, {"id": request_id})


# ═══ CHANNEL STATS ═══
async def update_channel_stats(chat_id: int, **kwargs):
    """Update channel stats — increment counters."""
    import datetime
    today = datetime.date.today().isoformat()
    existing = await table_select("channel_stats", filters={"chat_id": chat_id, "date": today}, single=True)
    if existing:
        updates = {}
        for k, v in kwargs.items():
            updates[k] = existing.get(k, 0) + v if isinstance(v, int) else v
        await table_update("channel_stats", updates, {"id": existing["id"]})
    else:
        await table_insert("channel_stats", {"chat_id": chat_id, "date": today, **kwargs})

async def get_channel_stats(chat_id: int) -> dict:
    rows = await table_select("channel_stats", filters={"chat_id": chat_id}, order="date.desc", limit=1)
    return rows[0] if rows else {}


# ═══ FORCE SUBSCRIBE ═══
async def get_force_sub_channels(chat_id: int) -> list:
    """Get force subscribe channels from managed_channels.force_subscribe_channels."""
    ch = await get_managed_channel(chat_id)
    if ch and ch.get("force_subscribe_enabled") and ch.get("force_subscribe_channels"):
        channels = ch["force_subscribe_channels"]
        if isinstance(channels, str):
            import json
            channels = json.loads(channels) if channels else []
        return channels if isinstance(channels, list) else []
    return []

async def add_force_sub_channel(target_chat_id: int, required_chat_id: int, title: str = ""):
    ch = await get_managed_channel(target_chat_id)
    if not ch:
        return
    channels = ch.get("force_subscribe_channels") or []
    if isinstance(channels, str):
        import json
        channels = json.loads(channels) if channels else []
    channels.append({"chat_id": required_chat_id, "title": title})
    await table_update("managed_channels", {
        "force_subscribe_enabled": True,
        "force_subscribe_channels": channels,
    }, {"chat_id": target_chat_id})

async def remove_force_sub_channel(target_chat_id: int, required_chat_id: int):
    ch = await get_managed_channel(target_chat_id)
    if not ch:
        return
    channels = ch.get("force_subscribe_channels") or []
    if isinstance(channels, str):
        import json
        channels = json.loads(channels) if channels else []
    channels = [c for c in channels if c.get("chat_id") != required_chat_id]
    await table_update("managed_channels", {
        "force_subscribe_channels": channels,
        "force_subscribe_enabled": bool(channels),
    }, {"chat_id": target_chat_id})

async def mark_force_sub_completed(user_id: int, chat_id: int):
    """Mark force subscribe as completed for a join request."""
    await table_update("join_requests", {"force_sub_completed": True}, {"user_id": user_id, "chat_id": chat_id, "status": "pending"})


# ═══ TEMPLATES ═══
async def get_templates(owner_id: int) -> list:
    return await table_select("templates", filters={"owner_id": owner_id}) or []

async def save_template(owner_id: int, name: str, content: str, content_type: str = "text", **kwargs):
    return await table_insert("templates", {
        "owner_id": owner_id, "name": name, "content": content, "content_type": content_type,
    })

async def delete_template(template_id: int):
    await table_delete("templates", {"template_id": template_id})


# ═══ AUTO POSTS ═══
async def get_auto_post_groups(owner_id: int) -> list:
    return await table_select("auto_post_groups", filters={"owner_id": owner_id}) or []

async def create_auto_post_schedule(owner_id: int, chat_id: int, content: str, interval_minutes: int = 60, **kwargs):
    return await table_insert("auto_post_schedules", {
        "owner_id": owner_id, "group_chat_id": chat_id,
        "content": content, "interval_minutes": interval_minutes,
        "is_active": True, "content_type": "text",
    })

async def get_active_auto_posts() -> list:
    return await table_select("auto_post_schedules", filters={"is_active": True}) or []


# ═══ BROADCASTS ═══
async def create_broadcast(owner_id: int, channel_id: int, content: str, content_type: str = "text", scheduled_at: str = None, **kwargs):
    data = {
        "owner_id": owner_id, "channel_id": channel_id,
        "content": content, "content_type": content_type,
        "status": "pending",
    }
    if scheduled_at:
        data["scheduled_at"] = scheduled_at
    result = await table_insert("broadcasts", data)
    return result[0] if isinstance(result, list) and result else data

async def get_broadcast_by_id(broadcast_id: int) -> Optional[dict]:
    return await table_select("broadcasts", filters={"broadcast_id": broadcast_id}, single=True)

async def get_broadcast_recipients(broadcast_id: int) -> list:
    """Get all end_user IDs for broadcast target channel."""
    bc = await get_broadcast_by_id(broadcast_id)
    if not bc:
        return []
    return await get_all_user_ids()

async def update_broadcast_progress(broadcast_id: int, **kwargs):
    await table_update("broadcasts", kwargs, {"broadcast_id": broadcast_id})

async def get_pending_broadcasts() -> list:
    return await table_select("broadcasts", filters={"status": "pending"}) or []


# ═══ REFERRAL STATS ═══
async def get_referral_stats(user_id: int) -> dict:
    owner = await get_owner(user_id)
    if owner:
        return {
            "referral_code": owner.get("referral_code", ""),
            "referral_count": owner.get("referral_count", 0),
            "referral_earnings": owner.get("referral_earnings", 0),
        }
    return {"referral_code": "", "referral_count": 0, "referral_earnings": 0}


# ═══ SETTINGS ═══
async def get_setting(key: str) -> Optional[str]:
    row = await table_select("platform_settings", filters={"key": key}, single=True)
    return row.get("value") if row else None

async def set_setting(key: str, value: str):
    await table_insert("platform_settings", {"key": key, "value": value}, upsert=True)

async def get_all_settings() -> list:
    return await table_select("platform_settings") or []


# ═══ GLOBAL STATS ═══
async def get_global_stats() -> dict:
    owners = await table_count("channel_owners")
    channels = await table_count("managed_channels")
    users = await table_count("end_users")
    return {"total_owners": owners, "total_channels": channels, "total_users": users}


# ═══ INTERACTIONS ═══
async def log_interaction(user_id: int, action: str):
    await table_insert("interactions", {"user_id": user_id, "action": action})


# ═══ SCHEDULER HELPERS ═══
async def get_due_auto_posts() -> list:
    """Get auto posts that are due to be sent."""
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    # Get active posts where next_run_at <= now or next_run_at is null
    posts = await table_select("auto_post_schedules", filters={"is_active": True})
    due = []
    for p in (posts or []):
        next_run = p.get("next_run_at")
        if not next_run or next_run <= now:
            due.append(p)
    return due

async def update_auto_post_next(schedule_id: int, interval_minutes: int = 60, **kwargs):
    """Update next run time for auto post."""
    import datetime
    next_run = (datetime.datetime.utcnow() + datetime.timedelta(minutes=interval_minutes)).isoformat()
    await table_update("auto_post_schedules", {"next_run_at": next_run}, {"schedule_id": schedule_id})

async def get_drip_channels() -> list:
    """Get channels with active drip approval."""
    channels = await table_select("managed_channels")
    return [c for c in (channels or []) if c.get("drip_rate") and c.get("drip_rate") > 0]
