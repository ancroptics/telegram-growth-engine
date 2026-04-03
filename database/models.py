"""Database models \u2014 all Supabase table operations."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional, List

from database.connection import table_select, table_insert, table_update, table_delete, rpc

logger = logging.getLogger(__name__)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# CHANNEL OWNERS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

async def get_or_create_owner(user_id: int, username: str = None, first_name: str = None) -> dict:
    data = {
        "user_id": user_id,
        "username": username or "",
        "first_name": first_name or "",
        "full_name": first_name or "",
        "tier": "free",
        "is_banned": False,
    }
    try:
        existing = await table_select("channel_owners", filters={"user_id": user_id}, single=True)
        if existing:
            return existing
        result = await table_insert("channel_owners", data, upsert=True)
        return result or data
    except Exception as e:
        logger.error(f"get_or_create_owner error: {e}")
        return data

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

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# MANAGED CHANNELS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

async def add_managed_channel(chat_id: int, chat_title: str, owner_id: int, chat_type: str = "channel") -> dict:
    data = {
        "chat_id": chat_id,
        "chat_title": chat_title,
        "owner_id": owner_id,
        "chat_type": chat_type,
        "auto_approve": True,
        "welcome_dm_enabled": True,
        "welcome_message": "Welcome to {channel_title}, {first_name}! \ud83c\udf89",
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

async def delete_managed_channel(chat_id: int):
    await table_delete("managed_channels", {"chat_id": chat_id})

async def get_all_channels() -> list:
    return await table_select("managed_channels") or []

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# END USERS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

async def get_or_create_end_user(user_id: int, username: str = None, first_name: str = None, referred_by: int = None) -> dict:
    data = {
        "user_id": user_id,
        "username": username or "",
        "first_name": first_name or "",
        "referred_by": referred_by,
        "is_blocked": False,
        "has_blocked_bot": False,
    }
    try:
        existing = await table_select("end_users", filters={"user_id": user_id}, single=True)
        if existing:
            return existing
        result = await table_insert("end_users", data, upsert=True)
        return result or data
    except Exception as e:
        logger.error(f"get_or_create_end_user error: {e}")
        return data

async def get_end_user(user_id: int) -> Optional[dict]:
    return await table_select("end_users", filters={"user_id": user_id}, single=True)

async def update_end_user(user_id: int, **kwargs):
    if kwargs:
        await table_update("end_users", kwargs, {"user_id": user_id})

async def get_referral_count(user_id: int) -> int:
    rows = await table_select("end_users", filters={"referred_by": user_id}) or []
    return len(rows)

async def get_end_users_for_channel(chat_id: int) -> list:
    return await table_select("channel_members", filters={"chat_id": chat_id}) or []

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# CHANNEL MEMBERS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

async def add_channel_member(chat_id: int, user_id: int, status: str = "pending") -> dict:
    data = {
        "chat_id": chat_id,
        "user_id": user_id,
        "status": status,
    }
    return await table_insert("channel_members", data, upsert=True) or data

async def update_member_status(chat_id: int, user_id: int, status: str):
    await table_update("channel_members", {"status": status}, {"chat_id": chat_id, "user_id": user_id})

async def get_pending_members(chat_id: int, limit: int = 10) -> list:
    return await table_select("channel_members", filters={"chat_id": chat_id, "status": "pending"}, limit=limit) or []

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# TEMPLATES & AUTO-POSTS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

async def create_template(owner_id: int, name: str, content: str, template_type: str = "text") -> Optional[dict]:
    data = {
        "owner_id": owner_id,
        "name": name,
        "content": content,
        "template_type": template_type,
    }
    return await table_insert("templates", data)

async def get_owner_templates(owner_id: int) -> list:
    return await table_select("templates", filters={"owner_id": owner_id}) or []

async def delete_template(template_id: int):
    await table_delete("templates", {"id": template_id})

async def create_auto_post(owner_id: int, chat_id: int, content: str, interval_minutes: int = 60) -> Optional[dict]:
    data = {
        "owner_id": owner_id,
        "chat_id": chat_id,
        "content": content,
        "interval_minutes": interval_minutes,
        "is_active": True,
    }
    return await table_insert("auto_posts", data)

async def get_active_auto_posts() -> list:
    return await table_select("auto_posts", filters={"is_active": True}) or []

async def get_owner_auto_posts(owner_id: int) -> list:
    return await table_select("auto_posts", filters={"owner_id": owner_id}) or []

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# BROADCASTS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

async def create_broadcast(owner_id: int, content: str, scheduled_at: str = None) -> Optional[dict]:
    data = {
        "owner_id": owner_id,
        "content": content,
        "status": "scheduled" if scheduled_at else "pending",
    }
    if scheduled_at:
        data["scheduled_at"] = scheduled_at
    return await table_insert("broadcasts", data)

async def get_pending_broadcasts() -> list:
    return await table_select("broadcasts", filters={"status": "pending"}) or []

async def get_scheduled_broadcasts() -> list:
    return await table_select("broadcasts", filters={"status": "scheduled"}) or []

async def update_broadcast_status(broadcast_id: int, status: str):
    await table_update("broadcasts", {"status": status}, {"id": broadcast_id})

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# SETTINGS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

async def get_setting(key: str) -> Optional[str]:
    row = await table_select("settings", filters={"key": key}, single=True)
    return row.get("value") if row else None

async def set_setting(key: str, value: str):
    existing = await table_select("settings", filters={"key": key}, single=True)
    if existing:
        await table_update("settings", {"value": value}, {"key": key})
    else:
        await table_insert("settings", {"key": key, "value": value})

async def get_force_sub_channels(owner_id: int) -> list:
    return await table_select("force_subscribe", filters={"owner_id": owner_id}) or []

async def add_force_sub(owner_id: int, chat_id: int, chat_title: str):
    return await table_insert("force_subscribe", {"owner_id": owner_id, "chat_id": chat_id, "chat_title": chat_title}, upsert=True)
