"""Watermark service."""
from database.models import get_owner_tier
from config import Config

async def get_watermark(channel: dict, owner_id: int) -> str:
    if not channel.get("watermark_enabled", True):
        return ""
    tier = await get_owner_tier(owner_id)
    if tier in ("premium", "business"):
        return ""
    bot_un = Config.BOT_USERNAME or "GrowthEngineBot"
    return f"\n\n━━━━━━━━━━━━━━━━━\n🤖 Powered by @{bot_un}"
