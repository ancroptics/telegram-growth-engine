"""Watermark service."""
import logging
from database.models import get_owner_tier

logger = logging.getLogger(__name__)


async def add_watermark(image_bytes: bytes, text: str) -> bytes:
    """Future: Add watermark to images."""
    return image_bytes


async def get_watermark(channel: dict, owner_id: int) -> str:
    """Return watermark text for free tier users."""
    try:
        tier = await get_owner_tier(owner_id)
        if tier == "free":
            return "\n\n---\nPowered by Telegram Growth Engine"
    except Exception:
        pass
    return ""
