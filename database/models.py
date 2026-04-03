"""Database models — async helpers for Supabase REST API.
Maps to the ACTUAL database schema in Supabase.
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


# ═══ END USERS ═══
async def get_or_create_end_user(user_id: int, username: str = None, first_name: str = None,
                                  language_code: str = None, source_channel: int = None):
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


# ═══ JOIN REQUESTS ═══
async def record_join_request(user_id: int, chat_id: int, username: str = None, first_name: str = None):
    return await table_insert("join_requests", {
        "user_id": user_id, "chat_id": chat_id,
        "username": username or "", "first_name": first_name or "",
        "status": "pending",
    })

async def get_pending_requests(chat_id: int, limit: int = 50) -> list:
    return await table_select("join_requests", filters={"chat_id": chat_id, "status": "pending"}, limit=limit) or []

async def update_join_request(request_id: int, **kwargs):
    await table_update("join_requests", kwargs, {"id": request_id})


# ═══ WELCOME MESSAGES (stored in managed_channels) ═══
async def get_welcome_message(chat_id: int) -> Optional[dict]:
    ch = await get_managed_channel(chat_id)
    if ch and ch.get("welcome_dm_enabled"):
        return {
            "chat_id": chat_id,
            "message_text": ch.get("welcome_message", "Welcome!"),
            "parse_mode": ch.get("welcome_parse_mode", "HTML"),
            "enabled": ch.get("welcome_dm_enabled", False),
            "media_type": ch.get("welcome_media_type"),
            "media_file_id": ch.get("welcome_media_file_id"),
        }
    return None

async def set_welcome_message(chat_id: int, message_text: str, parse_mode: str = "HTML"):
    await table_update("managed_channels", {
        "welcome_dm_enabled": True,
        "welcome_message": message_text,
        "welcome_parse_mode": parse_mode,
    }, {"chat_id": chat_id})


# ═══ FORCE SUBSCRIBE (stored in managed_channels.force_subscribe_channels jsonb) ═══
async def get_force_sub_rules(chat_id: int) -> list:
    ch = await get_managed_channel(chat_id)
    if ch and ch.get("force_subscribe_enabled") and ch.get("force_subscribe_channels"):
        channels = ch["force_subscribe_channels"]
        if isinstance(channels, list):
            return [{"target_chat_id": chat_id, "required_chat_id": c.get("chat_id"), "required_chat_title": c.get("title", "")} for c in channels]
    return []

async def add_force_sub_rule(target_chat_id: int, required_chat_id: int, required_chat_title: str = ""):
    ch = await get_managed_channel(target_chat_id)
    if not ch:
        return
    channels = ch.get("force_subscribe_channels") or []
    if isinstance(channels, str):
        import json
        channels = json.loads(channels) if channels else []
    channels.append({"chat_id": required_chat_id, "title": required_chat_title})
    await table_update("managed_channels", {
        "force_subscribe_enabled": True,
        "force_subscribe_channels": channels,
    }, {"chat_id": target_chat_id})


# ═══ TEMPLATES ═══
async def get_templates(owner_id: int) -> list:
    return await table_select("templates", filters={"owner_id": owner_id}) or []

async def get_template(template_id: int) -> Optional[dict]:
    return await table_select("templates", filters={"template_id": template_id}, single=True)

async def create_template(owner_id: int, name: str, content: str, content_type: str = "text"):
    return await table_insert("templates", {
        "owner_id": owner_id, "name": name, "content": content, "content_type": content_type,
    })

async def delete_template(template_id: int):
    await table_delete("templates", {"template_id": template_id})


# ═══ AUTO POSTS ═══
async def get_auto_posts(owner_id: int = None) -> list:
    filters = {"owner_id": owner_id} if owner_id else {}
    return await table_select("auto_post_schedules", filters=filters) or []

async def get_active_auto_posts() -> list:
    return await table_select("auto_post_schedules", filters={"is_active": True}) or []

async def create_auto_post(owner_id: int, chat_id: int, content: str, interval_minutes: int = 60):
    return await table_insert("auto_post_schedules", {
        "owner_id": owner_id, "group_chat_id": chat_id,
        "content": content, "interval_minutes": interval_minutes,
        "is_active": True, "content_type": "text",
    })


# ═══ BROADCASTS ═══
async def get_scheduled_broadcasts(owner_id: int = None, pending_only: bool = False) -> list:
    filters = {}
    if owner_id:
        filters["owner_id"] = owner_id
    if pending_only:
        filters["status"] = "pending"
    return await table_select("broadcasts", filters=filters) or []

async def create_broadcast(owner_id: int, chat_id: int, content: str, scheduled_at: str = None):
    data = {
        "owner_id": owner_id, "channel_id": chat_id,
        "content": content, "content_type": "text",
        "status": "pending",
    }
    if scheduled_at:
        data["scheduled_at"] = scheduled_at
    return await table_insert("broadcasts", data)

async def update_broadcast(broadcast_id: int, **kwargs):
    await table_update("broadcasts", kwargs, {"broadcast_id": broadcast_id})


# ═══ DRIP CAMPAIGNS (stored in managed_channels) ═══
async def get_drip_config(chat_id: int) -> Optional[dict]:
    ch = await get_managed_channel(chat_id)
    if ch:
        return {
            "chat_id": chat_id,
            "drip_rate": ch.get("drip_rate", 0),
            "drip_interval": ch.get("drip_interval", 60),
            "enabled": bool(ch.get("drip_rate")),
        }
    return None

async def set_drip_config(chat_id: int, rate: int, interval: int = 60):
    await table_update("managed_channels", {
        "drip_rate": rate, "drip_interval": interval,
    }, {"chat_id": chat_id})


# ═══ BOT SETTINGS (platform_settings) ═══
async def get_setting(key: str) -> Optional[str]:
    row = await table_select("platform_settings", filters={"key": key}, single=True)
    return row.get("value") if row else None

async def set_setting(key: str, value: str):
    await table_insert("platform_settings", {"key": key, "value": value}, upsert=True)


# ═══ ANALYTICS / STATS ═══
async def log_interaction(user_id: int, action: str):
    await table_insert("interactions", {"user_id": user_id, "action": action})

async def get_channel_stats(chat_id: int) -> dict:
    rows = await table_select("channel_stats", filters={"chat_id": chat_id}, order="date.desc", limit=1)
    return rows[0] if rows else {}

async def get_owner_stats(owner_id: int) -> dict:
    """Get aggregated stats for an owner."""
    channels = await get_owner_channels(owner_id)
    total_members = sum(c.get("member_count", 0) for c in channels)
    return {
        "total_channels": len(channels),
        "total_members": total_members,
    }
