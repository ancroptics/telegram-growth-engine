"""Watermark service for welcome DMs."""
import logging
from database.models import get_owner_tier

logger = logging.getLogger(__name__)


async def get_watermark(channel: dict, owner_id: int) -> str:
    """Return watermark text for free-tier users."""
    if channel.get("watermark_enabled") is False:
        return ""
    tier = await get_owner_tier(owner_id)
    if tier in ("premium", "business"):
        return ""
    return "\n\n\u2014 Powered by Telegram Growth Engine"
