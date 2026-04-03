"""Auto-create tables on startup."""
import logging

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_owners (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username TEXT DEFAULT '',
    first_name TEXT DEFAULT '',
    tier TEXT DEFAULT 'free',
    is_banned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS managed_channels (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    chat_id BIGINT UNIQUE NOT NULL,
    chat_title TEXT DEFAULT '',
    chat_type TEXT DEFAULT 'channel',
    auto_approve BOOLEAN DEFAULT FALSE,
    drip_rate INT DEFAULT 0,
    welcome_message TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS end_users (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username TEXT DEFAULT '',
    first_name TEXT DEFAULT '',
    referred_by BIGINT,
    has_blocked_bot BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS channel_members (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    template_type TEXT DEFAULT 'text',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auto_posts (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    interval_minutes INT DEFAULT 60,
    is_active BOOLEAN DEFAULT TRUE,
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    chat_id BIGINT,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    scheduled_at TIMESTAMPTZ,
    sent_count INT DEFAULT 0,
    failed_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS force_subscribe (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    chat_title TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(owner_id, chat_id)
);

CREATE TABLE IF NOT EXISTS force_sub_completions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, chat_id)
);

CREATE TABLE IF NOT EXISTS join_requests (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    username TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    approval_method TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chat_id, user_id)
);
"""

async def run_migrations():
    """Create tables if using direct PG."""
    from database.connection import _get_pool, DATABASE_URL
    if not DATABASE_URL:
        return
    try:
        pool = await _get_pool()
        if not pool:
            logger.warning("No PG pool - skipping migrations")
            return
        async with pool.acquire() as conn:
            await conn.execute(SCHEMA)
            logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
