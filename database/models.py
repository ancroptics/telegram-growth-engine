"""Database models - Supabase REST API."""
import logging
from datetime import datetime, timedelta
from database.connection import sb_select, sb_insert, sb_update, sb_upsert, sb_delete

logger = logging.getLogger(__name__)

async def get_or_create_owner(user_id, username=None, first_name=None, last_name=None):
    existing = await sb_select("channel_owners", {"user_id": f"eq.{user_id}"}, single=True)
    if existing:
        return existing
    data = {"user_id": user_id, "username": username or "", "first_name": first_name or "",
            "last_name": last_name or "", "tier": "free", "referral_code": f"ref_{user_id}",
            "total_referrals": 0, "total_channels": 0}
    return await sb_upsert("channel_owners", data) or data

async def get_owner(user_id):
    return await sb_select("channel_owners", {"user_id": f"eq.{user_id}"}, single=True)

async def ban_owner(user_id, reason=""):
    await sb_update("channel_owners", {"user_id": f"eq.{user_id}"}, {"is_banned": True, "ban_reason": reason})

async def unban_owner(user_id):
    await sb_update("channel_owners", {"user_id": f"eq.{user_id}"}, {"is_banned": False, "ban_reason": ""})

async def set_user_tier(user_id, tier, days=30):
    expires = (datetime.utcnow() + timedelta(days=days)).isoformat()
    await sb_update("channel_owners", {"user_id": f"eq.{user_id}"}, {"tier": tier, "tier_expires_at": expires})

async def get_all_owners():
    return await sb_select("channel_owners") or []

async def add_managed_channel(chat_id, chat_title, owner_id, chat_type="channel"):
    data = {"chat_id": chat_id, "chat_title": chat_title, "owner_id": owner_id, "chat_type": chat_type,
            "is_active": True, "auto_approve": True, "welcome_dm_enabled": True,
            "welcome_message": "Welcome to {channel_name}! \ud83c\udf89", "approve_mode": "instant",
            "force_subscribe_enabled": False, "total_approved": 0, "total_dm_sent": 0, "total_dm_failed": 0}
    result = await sb_upsert("managed_channels", data)
    owner = await get_owner(owner_id)
    if owner:
        await sb_update("channel_owners", {"user_id": f"eq.{owner_id}"},
                        {"total_channels": (owner.get("total_channels") or 0) + 1})
    return result

async def get_managed_channel(chat_id):
    return await sb_select("managed_channels", {"chat_id": f"eq.{chat_id}"}, single=True)

async def get_owner_channels(owner_id):
    return await sb_select("managed_channels", {"owner_id": f"eq.{owner_id}"}) or []

async def get_active_channels():
    return await sb_select("managed_channels", {"is_active": "eq.true"}) or []

async def remove_managed_channel(chat_id):
    await sb_update("managed_channels", {"chat_id": f"eq.{chat_id}"}, {"is_active": False})

async def update_channel_setting(chat_id, **kwargs):
    await sb_update("managed_channels", {"chat_id": f"eq.{chat_id}"}, kwargs)

async def increment_channel_stat(chat_id, **kwargs):
    ch = await get_managed_channel(chat_id)
    if not ch:
        return
    updates = {k: (ch.get(k) or 0) + v for k, v in kwargs.items()}
    await sb_update("managed_channels", {"chat_id": f"eq.{chat_id}"}, updates)

async def get_or_create_end_user(user_id, username=None, first_name=None, last_name=None,
                                  language_code=None, source=None, source_channel=None):
    existing = await sb_select("end_users", {"user_id": f"eq.{user_id}"}, single=True)
    if existing:
        return existing
    data = {"user_id": user_id, "username": username or "", "first_name": first_name or "",
            "last_name": last_name or "", "language_code": language_code or "",
            "source": source or "organic", "source_channel": source_channel, "is_blocked": False}
    return await sb_upsert("end_users", data) or data

async def mark_user_blocked(user_id):
    await sb_update("end_users", {"user_id": f"eq.{user_id}"}, {"is_blocked": True})

async def get_all_user_ids():
    users = await sb_select("end_users", {"is_blocked": "eq.false", "select": "user_id"}) or []
    return [u["user_id"] for u in users]

async def get_channel_users(chat_id):
    return await sb_select("join_requests", {"chat_id": f"eq.{chat_id}", "status": "eq.approved", "select": "user_id"}) or []

async def log_join_request(user_id, chat_id, username=None, first_name=None, language_code=None, status="pending"):
    data = {"user_id": user_id, "chat_id": chat_id, "username": username or "", "first_name": first_name or "",
            "language_code": language_code or "", "status": status, "requested_at": datetime.utcnow().isoformat()}
    return await sb_insert("join_requests", data)

async def approve_join_request_db(user_id, chat_id, method="auto"):
    await sb_update("join_requests", {"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"},
                    {"status": "approved", "approve_method": method, "approved_at": datetime.utcnow().isoformat()})

async def update_join_request_dm(user_id, chat_id, success, message_id=None, reason=None):
    data = {"dm_sent": success, "dm_sent_at": datetime.utcnow().isoformat()}
    if message_id:
        data["dm_message_id"] = message_id
    if reason:
        data["dm_fail_reason"] = reason
    await sb_update("join_requests", {"user_id": f"eq.{user_id}", "chat_id": f"eq.{chat_id}"}, data)

async def get_force_sub_channels(chat_id):
    ch = await get_managed_channel(chat_id)
    if not ch or not ch.get("force_subscribe_enabled"):
        return []
    return []

async def mark_force_sub_required(user_id, chat_id):
    pass

async def create_broadcast(owner_id, channel_id, content):
    data = {"owner_id": owner_id, "channel_id": channel_id, "content": content[:500],
            "status": "sending", "created_at": datetime.utcnow().isoformat()}
    return await sb_insert("broadcasts", data)

async def update_broadcast(broadcast_id, **kwargs):
    await sb_update("broadcasts", {"id": f"eq.{broadcast_id}"}, kwargs)

async def get_templates(owner_id):
    return await sb_select("templates", {"owner_id": f"eq.{owner_id}"}) or []

async def get_template(owner_id, name):
    return await sb_select("templates", {"owner_id": f"eq.{owner_id}", "name": f"eq.{name}"}, single=True)

async def save_template(owner_id, name, tpl_type, content):
    return await sb_upsert("templates", {"owner_id": owner_id, "name": name, "type": tpl_type, "content": content})

async def delete_template(owner_id, name):
    await sb_delete("templates", {"owner_id": f"eq.{owner_id}", "name": f"eq.{name}"})

async def update_daily_stats(chat_id, joins=0, approvals=0, dms_sent=0, dms_failed=0):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    existing = await sb_select("daily_stats", {"chat_id": f"eq.{chat_id}", "date": f"eq.{today}"}, single=True)
    if existing:
        data = {"joins": (existing.get("joins") or 0) + joins, "approvals": (existing.get("approvals") or 0) + approvals,
                "dms_sent": (existing.get("dms_sent") or 0) + dms_sent, "dms_failed": (existing.get("dms_failed") or 0) + dms_failed}
        await sb_update("daily_stats", {"chat_id": f"eq.{chat_id}", "date": f"eq.{today}"}, data)
    else:
        await sb_insert("daily_stats", {"chat_id": chat_id, "date": today, "joins": joins,
                                         "approvals": approvals, "dms_sent": dms_sent, "dms_failed": dms_failed})

async def get_channel_daily_stats(chat_id, days=7):
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    return await sb_select("daily_stats", {"chat_id": f"eq.{chat_id}", "date": f"gte.{cutoff}", "order": "date.desc"}) or []

async def get_global_stats():
    owners = await sb_select("channel_owners", {"select": "user_id"}) or []
    channels = await sb_select("managed_channels", {"select": "chat_id"}) or []
    users = await sb_select("end_users", {"select": "user_id"}) or []
    premium = await sb_select("channel_owners", {"tier": "neq.free", "select": "user_id"}) or []
    clones = await sb_select("bot_clones", {"select": "id"}) or []
    return {"total_owners": len(owners), "total_channels": len(channels), "total_users": len(users),
            "premium_owners": len(premium), "total_clones": len(clones)}

async def process_referral(referrer_id, referred_id):
    owner = await get_owner(referrer_id)
    if not owner:
        return
    await sb_update("channel_owners", {"user_id": f"eq.{referrer_id}"},
                    {"total_referrals": (owner.get("total_referrals") or 0) + 1})
