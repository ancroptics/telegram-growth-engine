"""Database initialization — verify tables exist."""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

REQUIRED_TABLES = [
    "channel_owners", "managed_channels", "end_users", "join_requests",
    "templates", "broadcasts", "auto_post_schedules", "platform_settings",
    "interactions", "channel_stats", "daily_stats",
]


async def run_migrations():
    """Verify required tables exist."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("No Supabase config - skipping verification")
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    missing = []
    async with httpx.AsyncClient(timeout=10) as client:
        for table in REQUIRED_TABLES:
            try:
                resp = await client.get(
                    f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1",
                    headers=headers
                )
                if resp.status_code != 200:
                    missing.append(table)
            except Exception:
                missing.append(table)

    if missing:
        logger.warning(f"Missing tables: {missing}")
    else:
        logger.info("All required tables verified")
