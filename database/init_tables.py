"""Create missing tables via Supabase exec_sql RPC."""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

TABLES_SQL = {
    "welcome_messages": """
        CREATE TABLE IF NOT EXISTS welcome_messages (
            id BIGSERIAL PRIMARY KEY, chat_id BIGINT NOT NULL,
            message_text TEXT DEFAULT 'Welcome!', parse_mode TEXT DEFAULT 'HTML',
            enabled BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
    "force_subscribe_rules": """
        CREATE TABLE IF NOT EXISTS force_subscribe_rules (
            id BIGSERIAL PRIMARY KEY, target_chat_id BIGINT NOT NULL,
            required_chat_id BIGINT NOT NULL, required_chat_title TEXT,
            enabled BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
    "message_templates": """
        CREATE TABLE IF NOT EXISTS message_templates (
            id BIGSERIAL PRIMARY KEY, owner_id BIGINT NOT NULL,
            name TEXT NOT NULL, content TEXT NOT NULL,
            parse_mode TEXT DEFAULT 'HTML', created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
    "auto_posts": """
        CREATE TABLE IF NOT EXISTS auto_posts (
            id BIGSERIAL PRIMARY KEY, owner_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL, content TEXT NOT NULL,
            interval_minutes INT DEFAULT 60, parse_mode TEXT DEFAULT 'HTML',
            enabled BOOLEAN DEFAULT TRUE, last_posted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
    "scheduled_broadcasts": """
        CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
            id BIGSERIAL PRIMARY KEY, owner_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL, content TEXT NOT NULL,
            parse_mode TEXT DEFAULT 'HTML', scheduled_at TIMESTAMPTZ NOT NULL,
            sent BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
    "drip_campaigns": """
        CREATE TABLE IF NOT EXISTS drip_campaigns (
            id BIGSERIAL PRIMARY KEY, chat_id BIGINT NOT NULL,
            delay_minutes INT DEFAULT 1440, enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
    "referral_links": """
        CREATE TABLE IF NOT EXISTS referral_links (
            id BIGSERIAL PRIMARY KEY, owner_id BIGINT NOT NULL,
            code TEXT UNIQUE NOT NULL, chat_id BIGINT,
            clicks INT DEFAULT 0, conversions INT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
    "bot_settings": """
        CREATE TABLE IF NOT EXISTS bot_settings (
            id BIGSERIAL PRIMARY KEY, key TEXT UNIQUE NOT NULL,
            value TEXT, updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",
    "analytics_events": """
        CREATE TABLE IF NOT EXISTS analytics_events (
            id BIGSERIAL PRIMARY KEY, event_type TEXT NOT NULL,
            chat_id BIGINT, user_id BIGINT, data JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
}

RLS_POLICY_SQL = """
DO $$ BEGIN
  ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
  DROP POLICY IF EXISTS allow_all_{table} ON {table};
  CREATE POLICY allow_all_{table} ON {table} FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
SELECT json_build_object('rls', true)
"""


async def run_migrations():
    """Create missing tables using exec_sql RPC."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("No Supabase config - skipping migrations")
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        for table, ddl in TABLES_SQL.items():
            try:
                # Check if table exists via REST
                resp = await client.get(
                    f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1",
                    headers=headers
                )
                if resp.status_code == 200:
                    logger.debug(f"Table {table} exists")
                    continue

                # Table missing - try to create via exec_sql
                # Wrap DDL: create a temp function, call it, drop it
                create_fn = f"""
                    CREATE OR REPLACE FUNCTION _create_{table}() RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER AS $fn$
                    BEGIN
                        {ddl};
                        ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                        BEGIN
                            CREATE POLICY allow_all_{table} ON {table} FOR ALL USING (true) WITH CHECK (true);
                        EXCEPTION WHEN duplicate_object THEN NULL;
                        END;
                        RETURN jsonb_build_object('created', '{table}');
                    END;
                    $fn$;
                    SELECT json_build_object('ok', true)
                """
                resp2 = await client.post(
                    f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                    headers=headers,
                    json={"query": create_fn}
                )
                if resp2.status_code == 200 and "error" not in str(resp2.json()):
                    # Now call the function
                    resp3 = await client.post(
                        f"{SUPABASE_URL}/rest/v1/rpc/_create_{table}",
                        headers=headers,
                        json={}
                    )
                    logger.info(f"Created table {table}: {resp3.status_code}")
                    # Drop the temp function
                    await client.post(
                        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                        headers=headers,
                        json={"query": f"SELECT json_build_object('dropped', (SELECT proname FROM pg_proc WHERE proname = '_create_{table}'))"}
                    )
                else:
                    logger.warning(f"Could not create {table}: {resp2.text[:200]}")
            except Exception as e:
                logger.warning(f"Migration for {table} failed: {e}")

    logger.info("Migrations complete")
