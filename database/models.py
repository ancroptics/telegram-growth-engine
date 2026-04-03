"""Database models — async helpers for Supabase (REST or direct PG)."""
import logging
from typing import Optional
from database.connection import table_select, table_insert, table_update, table_delete

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
    await table_delete("managed_channels", {"chat_id": chat_id})

async def get_all_channels() -> list:
    return await table_select("managed_channels") or []


# ═══ END USERS ═══
async def get_or_create_end_user(user_id: int, username: str = None, first_name: str = None, referred_by: int = None):
    try:
        existing = await table_select("end_users", filters={"user_id": user_id}, single=True)
        if existing:
            return existing
        data = {"user_id": user_id, "username": username or "", "first_name": first_name or ""}
        if referred_by:
            data["referred_by"] = referred_by
        result = await table_insert("end_users", data, upsert=True)
        return result[0] if isinstance(result, list) and result else data
    except Exception as e:
        logger.error(f"get_or_create_end_user failed: {e}")
        return {"user_id": user_id, "username": username or "", "first_name": first_name or ""}

async def get_end_user(user_id: int) -> Optional[dict]:
    return await table_select("end_users", filters={"user_id": user_id}, single=True)

async def update_end_user(user_id: int, **kwargs):
    await table_update("end_users", kwargs, {"user_id": user_id})

async def get_referral_count(user_id: int) -> int:
    rows = await table_select("end_users", filters={"referred_by": user_id})
    return len(rows) if rows else 0

async def get_end_users_for_channel(chat_id: int) -> list:
    return await table_select("channel_members", filters={"chat_id": chat_id}) or []


# ═══ CHANNEL MEMBERS ═══
async def add_channel_member(chat_id: int, user_id: int, status: str = "pending"):
    return await table_insert("channel_members", {
        "chat_id": chat_id, "user_id": user_id, "status": status
    }, upsert=True)

async def update_member_status(chat_id: int, user_id: int, status: str):
    await table_update("channel_members", {"status": status}, {"chat_id": chat_id, "user_id": user_id})

async def get_pending_members(chat_id: int) -> list:
    return await table_select("channel_members", filters={"chat_id": chat_id, "status": "pending"}) or []


# ═══ TEMPLATES ═══
async def create_template(owner_id: int, name: str, content: str, template_type: str = "text"):
    return await table_insert("templates", {
        "owner_id": owner_id, "name": name, "content": content, "template_type": template_type
    })

async def get_owner_templates(owner_id: int) -> list:
    return await table_select("templates", filters={"owner_id": owner_id}) or []

async def get_templates(owner_id: int) -> list:
    return await get_owner_templates(owner_id)

async def save_template(owner_id: int, name: str, content: str, template_type: str = "text"):
    return await create_template(owner_id, name, content, template_type)

async def delete_template(template_id: int):
    await table_delete("templates", {"id": template_id})


# ═══ AUTO POST ═══
async def create_auto_post(owner_id: int, chat_id: int, content: str, interval_minutes: int = 60):
    return await table_insert("auto_posts", {
        "owner_id": owner_id, "chat_id": chat_id,
        "content": content, "interval_minutes": interval_minutes, "is_active": True
    })

async def get_active_auto_posts() -> list:
    return await table_select("auto_posts", filters={"is_active": True}) or []

async def get_owner_auto_posts(owner_id: int) -> list:
    return await table_select("auto_posts", filters={"owner_id": owner_id}) or []

async def get_auto_post_groups(owner_id: int) -> list:
    return await get_owner_auto_posts(owner_id)

async def create_auto_post_schedule(owner_id: int, chat_id: int, content: str, interval_minutes: int = 60):
    return await create_auto_post(owner_id, chat_id, content, interval_minutes)


# ═══ BROADCASTS ═══
async def create_broadcast(owner_id: int, chat_id: int, content: str, scheduled_at=None):
    return await table_insert("broadcasts", {
        "owner_id": owner_id, "chat_id": chat_id,
        "content": content, "status": "pending",
        "scheduled_at": scheduled_at,
    })

async def get_pending_broadcasts() -> list:
    return await table_select("broadcasts", filters={"status": "pending"}) or []

async def get_scheduled_broadcasts() -> list:
    return await table_select("broadcasts", filters={"status": "scheduled"}) or []

async def update_broadcast_status(broadcast_id: int, status: str):
    await table_update("broadcasts", {"status": status}, {"id": broadcast_id})

async def get_broadcast_by_id(broadcast_id: int) -> Optional[dict]:
    return await table_select("broadcasts", filters={"id": broadcast_id}, single=True)

async def get_broadcast_recipients(broadcast_id: int) -> list:
    return await get_all_user_ids()

async def update_broadcast_progress(broadcast_id: int, sent: int, failed: int):
    await table_update("broadcasts", {"sent_count": sent, "failed_count": failed}, {"id": broadcast_id})

async def mark_user_blocked(user_id: int):
    await table_update("end_users", {"has_blocked_bot": True}, {"user_id": user_id})


# ═══ SETTINGS ═══
async def get_setting(key: str, default=None):
    row = await table_select("settings", filters={"key": key}, single=True)
    return row.get("value", default) if row else default

async def set_setting(key: str, value: str):
    await table_insert("settings", {"key": key, "value": value}, upsert=True)

async def get_all_settings() -> list:
    return await table_select("settings") or []


# ═══ FORCE SUBSCRIBE ═══
async def get_force_sub_channels(owner_id: int) -> list:
    return await table_select("force_subscribe", filters={"owner_id": owner_id}) or []

async def add_force_sub(owner_id: int, chat_id: int, chat_title: str):
    return await table_insert("force_subscribe", {
        "owner_id": owner_id, "chat_id": chat_id, "chat_title": chat_title
    }, upsert=True)

async def add_force_sub_channel(owner_id: int, chat_id: int, chat_title: str):
    return await add_force_sub(owner_id, chat_id, chat_title)

async def remove_force_sub_channel(owner_id: int, chat_id: int):
    await table_delete("force_subscribe", {"owner_id": owner_id, "chat_id": chat_id})

async def mark_force_sub_completed(user_id: int, chat_id: int):
    await table_insert("force_sub_completions", {
        "user_id": user_id, "chat_id": chat_id,
    }, upsert=True)


# ═══ JOIN REQUESTS ═══
async def log_join_request(chat_id: int, user_id: int, username: str = None):
    await table_insert("join_requests", {
        "chat_id": chat_id, "user_id": user_id,
        "username": username or "", "status": "pending",
    }, upsert=True)

async def approve_join_request_db(chat_id: int, user_id: int, method: str = "auto"):
    await table_update("join_requests", {"status": "approved", "approval_method": method}, {"chat_id": chat_id, "user_id": user_id})
    await add_channel_member(chat_id, user_id, status="active")

async def update_channel_stats(chat_id: int, **kwargs):
    await table_update("managed_channels", kwargs, {"chat_id": chat_id})


# ═══ STATS ═══
async def get_referral_stats(user_id: int) -> dict:
    count = await get_referral_count(user_id)
    return {"total_referrals": count, "user_id": user_id}

async def get_channel_stats(chat_id: int) -> dict:
    channel = await get_managed_channel(chat_id)
    members = await get_end_users_for_channel(chat_id)
    return {
        "chat_id": chat_id,
        "title": channel.get("chat_title", "") if channel else "",
        "member_count": len(members),
    }

async def get_global_stats() -> dict:
    owners = await table_select("channel_owners") or []
    channels = await table_select("managed_channels") or []
    users = await table_select("end_users") or []
    return {
        "total_owners": len(owners),
        "total_channels": len(channels),
        "total_users": len(users),
    }


async def get_due_auto_posts() -> list:
    """Get auto posts that are due to be sent."""
    return await get_active_auto_posts()


# ═══ MISSING FUNCTIONS (referenced by scheduler & handlers) ═══

async def update_auto_post_next(schedule_id: int, interval_minutes: int):
    """Update next_run_at for an auto post schedule."""
    from datetime import datetime, timedelta
    next_run = datetime.utcnow() + timedelta(minutes=interval_minutes)
    await table_update("auto_posts", {"next_run_at": next_run.isoformat()}, {"id": schedule_id})


async def get_drip_channels() -> list:
    """Get channels that have drip approval enabled (drip_rate > 0)."""
    channels = await table_select("managed_channels") or []
    return [ch for ch in channels if ch.get("drip_rate", 0) > 0]


async def get_pending_requests(chat_id: int) -> list:
    """Get pending join requests for a channel."""
    return await table_select("join_requests", filters={"chat_id": chat_id, "status": "pending"}) or []
