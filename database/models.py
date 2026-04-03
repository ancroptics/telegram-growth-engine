"""Database models — all Supabase table operations."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional, List

from database.connection import table_select, table_insert, table_update, table_delete, rpc

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# CHANNEL OWNERS
# ═══════════════════════════════════════════

async def get_or_create_owner(user_id: int, username: str = None, first_name: str = None) -> dict:
    existing = await table_select("channel_owners", filters={"user_id": user_id}, single=True)
    if existing:
        return existing
    data = {
        "user_id": user_id,
        "username": username or "",
        "first_name": first_name or "",
        "full_name": first_name or "",
        "tier": "free",
        "is_banned": False,
    }
    result = await table_insert("channel_owners", data, upsert=True)
    return result or data


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


async def get_all_owners(limit: int = 50) -> list:
    return await table_select("channel_owners", limit=limit, order="created_at.desc") or []


async def get_all_user_ids() -> list:
    rows = await table_select("end_users", columns="user_id") or []
    return [r["user_id"] for r in rows]


# ═══════════════════════════════════════════
# MANAGED CHANNELS
# ═══════════════════════════════════════════

async def add_managed_channel(chat_id: int, chat_title: str, owner_id: int, chat_type: str = "channel") -> dict:
    data = {
        "chat_id": chat_id,
        "chat_title": chat_title,
        "owner_id": owner_id,
        "chat_type": chat_type,
        "auto_approve": True,
        "welcome_dm_enabled": True,
        "welcome_message": "Welcome to {channel_title}, {first_name}! 🎉",
        "drip_enabled": False,
        "drip_rate": 1,
        "force_subscribe_enabled": False,
    }
    return await table_insert("managed_channels", data, upsert=True) or data


async def get_managed_channel(chat_id: int) -> Optional[dict]:
    return await table_select("managed_channels", filters={"chat_id": chat_id}, single=True)


async def get_owner_channels(owner_id: int) -> list:
    return await table_select("managed_channels", filters={"owner_id": owner_id}) or []


async def update_channel_setting(chat_id: int, **kwargs):
    if kwargs:
        await table_update("managed_channels", kwargs, {"chat_id": chat_id})


async def remove_managed_channel(chat_id: int):
    await table_delete("managed_channels", {"chat_id": chat_id})


# ═══════════════════════════════════════════
# END USERS
# ═══════════════════════════════════════════

async def get_or_create_end_user(user_id: int, username: str = None, first_name: str = None, referred_by: int = None) -> dict:
    existing = await table_select("end_users", filters={"user_id": user_id}, single=True)
    if existing:
        return existing
    data = {
        "user_id": user_id,
        "username": username or "",
        "first_name": first_name or "",
        "referred_by": referred_by,
        "is_blocked": False,
        "has_blocked_bot": False,
    }
    result = await table_insert("end_users", data, upsert=True)
    return result or data


async def mark_user_blocked(user_id: int):
    await table_update("end_users", {"has_blocked_bot": True, "is_blocked": True}, {"user_id": user_id})


# ═══════════════════════════════════════════
# JOIN REQUESTS
# ═══════════════════════════════════════════

async def log_join_request(user_id: int, chat_id: int, status: str = "pending") -> dict:
    data = {
        "user_id": user_id,
        "chat_id": chat_id,
        "status": status,
    }
    return await table_insert("join_requests", data) or data


async def approve_join_request_db(user_id: int, chat_id: int, method: str = "auto"):
    rows = await table_select("join_requests", filters={"user_id": user_id, "chat_id": chat_id}, order="created_at.desc", limit=1)
    if rows and isinstance(rows, list) and rows:
        req_id = rows[0].get("id")
        if req_id:
            await table_update("join_requests", {"status": "approved", "approved_via": method}, {"id": req_id})


async def get_pending_requests(chat_id: int) -> list:
    return await table_select("join_requests", filters={"chat_id": chat_id, "status": "pending"}, order="created_at.asc") or []


# ═══════════════════════════════════════════
# DAILY STATS
# ═══════════════════════════════════════════

async def update_channel_stats(chat_id: int, approved: int = 0, dms_sent: int = 0, requests: int = 0):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = await table_select("daily_stats", filters={"chat_id": chat_id, "date": today}, single=True)
    if existing:
        await table_update("daily_stats", {
            "requests_approved": (existing.get("requests_approved", 0) or 0) + approved,
            "dms_sent": (existing.get("dms_sent", 0) or 0) + dms_sent,
            "join_requests": (existing.get("join_requests", 0) or 0) + requests,
        }, {"id": existing["id"]})
    else:
        await table_insert("daily_stats", {
            "chat_id": chat_id,
            "date": today,
            "requests_approved": approved,
            "dms_sent": dms_sent,
            "join_requests": requests,
        })


async def get_channel_stats(chat_id: int, days: int = 7) -> list:
    return await table_select("daily_stats", filters={"chat_id": chat_id}, order="date.desc", limit=days) or []


# ═══════════════════════════════════════════
# REFERRALS
# ═══════════════════════════════════════════

async def get_referral_stats(user_id: int) -> dict:
    rows = await table_select("end_users", filters={"referred_by": user_id}) or []
    return {"total": len(rows), "active": len([r for r in rows if not r.get("has_blocked_bot")])}


# ═══════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════

async def get_templates(owner_id: int) -> list:
    return await table_select("templates", filters={"owner_id": owner_id}) or []


async def save_template(owner_id: int, name: str, content_type: str, content: str = None, media_file_id: str = None, caption: str = None):
    data = {
        "owner_id": owner_id,
        "name": name,
        "content_type": content_type,
        "content": content or "",
        "media_file_id": media_file_id or "",
        "caption": caption or "",
    }
    return await table_insert("templates", data, upsert=True)


async def delete_template(owner_id: int, name: str):
    rows = await table_select("templates", filters={"owner_id": owner_id, "name": name})
    if rows:
        await table_delete("templates", {"id": rows[0]["id"]})


# ═══════════════════════════════════════════
# BROADCASTS
# ═══════════════════════════════════════════

async def create_broadcast(owner_id: int, channel_id: int, content_type: str, content: str = None, media_file_id: str = None, caption: str = None) -> int:
    data = {
        "owner_id": owner_id,
        "channel_id": channel_id,
        "content_type": content_type,
        "content": content or "",
        "media_file_id": media_file_id or "",
        "caption": caption or "",
        "status": "draft",
    }
    result = await table_insert("broadcasts", data)
    return result.get("id", 0) if result else 0


async def get_broadcast_by_id(bc_id: int) -> Optional[dict]:
    return await table_select("broadcasts", filters={"id": bc_id}, single=True)


async def get_broadcast_recipients(owner_id: int, channel_id: int = None) -> list:
    if channel_id:
        rows = await table_select("join_requests", columns="user_id", filters={"chat_id": channel_id, "status": "approved"}) or []
    else:
        rows = await table_select("end_users", columns="user_id") or []
    return list(set(r["user_id"] for r in rows))


async def update_broadcast_progress(bc_id: int, sent: int, failed: int, blocked: int, status: str):
    await table_update("broadcasts", {
        "sent_count": sent, "failed_count": failed,
        "blocked_count": blocked, "status": status,
    }, {"id": bc_id})


async def get_scheduled_broadcasts() -> list:
    return await table_select("broadcasts", filters={"status": "scheduled"}) or []


# ═══════════════════════════════════════════
# AUTO POSTER
# ═══════════════════════════════════════════

async def get_auto_post_groups(owner_id: int) -> list:
    return await table_select("auto_post_groups", filters={"owner_id": owner_id}) or []


async def create_auto_post_schedule(owner_id: int, group_chat_id: int, content: str, content_type: str, interval_minutes: int) -> int:
    data = {
        "owner_id": owner_id,
        "group_chat_id": group_chat_id,
        "content": content,
        "content_type": content_type,
        "interval_minutes": interval_minutes,
        "is_active": True,
    }
    result = await table_insert("auto_post_schedules", data)
    return result.get("schedule_id", 0) if result else 0


async def get_due_auto_posts() -> list:
    now = datetime.now(timezone.utc).isoformat()
    rows = await table_select("auto_post_schedules", filters={"is_active": True}) or []
    due = []
    for r in rows:
        next_run = r.get("next_run_at")
        if not next_run or next_run <= now:
            due.append(r)
    return due


async def update_auto_post_next(schedule_id: int, interval_minutes: int):
    from datetime import timedelta
    next_run = (datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)).isoformat()
    await table_update("auto_post_schedules", {"next_run_at": next_run}, {"schedule_id": schedule_id})


# ═══════════════════════════════════════════
# DRIP MODE
# ═══════════════════════════════════════════

async def get_drip_channels() -> list:
    return await table_select("managed_channels", filters={"drip_enabled": True}) or []


# ═══════════════════════════════════════════
# FORCE SUBSCRIBE
# ═══════════════════════════════════════════

async def get_force_sub_channels(chat_id: int) -> list:
    ch = await get_managed_channel(chat_id)
    if not ch:
        return []
    fs = ch.get("force_subscribe_channels")
    if not fs:
        return []
    if isinstance(fs, str):
        import json
        try:
            return json.loads(fs)
        except Exception:
            return []
    return fs if isinstance(fs, list) else []


async def add_force_sub_channel(chat_id: int, username: str):
    channels = await get_force_sub_channels(chat_id)
    if username not in channels:
        channels.append(username)
    import json
    await update_channel_setting(chat_id, force_subscribe_channels=json.dumps(channels))


async def remove_force_sub_channel(chat_id: int, item):
    channels = await get_force_sub_channels(chat_id)
    username = item if isinstance(item, str) else item.get("username", "")
    if username in channels:
        channels.remove(username)
    import json
    await update_channel_setting(chat_id, force_subscribe_channels=json.dumps(channels))


async def mark_force_sub_completed(user_id: int, chat_id: int):
    pass


# ═══════════════════════════════════════════
# GLOBAL STATS / ADMIN
# ═══════════════════════════════════════════

async def get_global_stats() -> dict:
    owners = await table_select("channel_owners", columns="user_id") or []
    channels = await table_select("managed_channels", columns="chat_id") or []
    users = await table_select("end_users", columns="user_id") or []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_stats = await table_select("daily_stats", filters={"date": today}) or []
    return {
        "total_owners": len(owners),
        "active_channels": len(channels),
        "total_users": len(users),
        "today_requests": sum(s.get("join_requests", 0) or 0 for s in today_stats),
        "today_approved": sum(s.get("requests_approved", 0) or 0 for s in today_stats),
        "today_dms": sum(s.get("dms_sent", 0) or 0 for s in today_stats),
    }


async def get_all_settings() -> dict:
    try:
        rows = await table_select("settings") or []
        return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


async def set_setting(key: str, value: str):
    try:
        await table_insert("settings", {"key": key, "value": value}, upsert=True)
    except Exception as e:
        logger.error(f"Failed to set setting {key}: {e}")


# ═══════════════════════════════════════════
# BOT CLONES
# ═══════════════════════════════════════════

async def get_bot_clones(owner_id: int) -> list:
    return await table_select("bot_clones", filters={"owner_id": owner_id}) or []


async def create_bot_clone(owner_id: int, clone_token: str, clone_username: str) -> dict:
    data = {
        "owner_id": owner_id,
        "clone_token": clone_token,
        "clone_username": clone_username,
        "is_active": True,
    }
    return await table_insert("bot_clones", data) or data
