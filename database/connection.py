"""Async PostgreSQL connection via Supabase REST API (HTTPS).

Uses the PostgREST RPC endpoint to execute SQL queries over HTTPS,
bypassing port restrictions on Render free tier.
"""
import logging
import re
import httpx
from config import Config

logger = logging.getLogger(__name__)

SUPABASE_URL = "https://yholtsvlkpcxclwecpfu.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlob2x0c3Zsa3BjeGNsd2VjcGZ1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTA2OTc4NSwiZXhwIjoyMDkwNjQ1Nzg1fQ.JRtuZAN5M0n18GvZQrP0EfeLlMJBDQP2u2SpuKrK2Cw"

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}


def _interpolate_params(query: str, args: tuple) -> str:
    """Replace $1, $2, ... placeholders with properly escaped values."""
    if not args:
        return query

    def replacer(match):
        idx = int(match.group(1)) - 1
        if idx >= len(args):
            return match.group(0)
        val = args[idx]
        if val is None:
            return "NULL"
        elif isinstance(val, bool):
            return "TRUE" if val else "FALSE"
        elif isinstance(val, (int, float)):
            return str(val)
        elif isinstance(val, str):
            escaped = val.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(val, list):
            import json
            escaped = json.dumps(val).replace("'", "''")
            return f"'{escaped}'::jsonb"
        else:
            escaped = str(val).replace("'", "''")
            return f"'{escaped}'"

    return re.sub(r'\$(\d+)', replacer, query)


class Database:
    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            cls._client = httpx.AsyncClient(timeout=30.0)
        return cls._client

    @classmethod
    async def _call_rpc(cls, sql: str, args: tuple = ()) -> list:
        """Execute SQL via Supabase RPC endpoint."""
        full_sql = _interpolate_params(sql, args)
        client = cls._get_client()
        try:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/exec_query",
                headers=HEADERS,
                json={"sql_text": full_sql},
            )
            resp.raise_for_status()
            result = resp.json()
            if isinstance(result, dict) and "error" in result:
                logger.error(f"SQL error: {result['error']}")
                raise Exception(result["error"])
            return result if isinstance(result, list) else []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling RPC: {e.response.status_code} {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"RPC call failed: {e}")
            raise

    @classmethod
    async def _call_dml(cls, sql: str, args: tuple = ()) -> str:
        """Execute DML (INSERT/UPDATE/DELETE) via Supabase RPC endpoint."""
        full_sql = _interpolate_params(sql, args)
        client = cls._get_client()
        try:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/exec_dml",
                headers=HEADERS,
                json={"sql_text": full_sql},
            )
            resp.raise_for_status()
            result = resp.json()
            if isinstance(result, dict) and "error" in result:
                logger.error(f"SQL error: {result['error']}")
                raise Exception(result["error"])
            return "OK"
        except Exception as e:
            logger.error(f"DML call failed: {e}")
            raise

    @classmethod
    async def get_pool(cls):
        """Compatibility method - tests connection."""
        client = cls._get_client()
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_query",
            headers=HEADERS,
            json={"sql_text": "SELECT 1 as ok"},
        )
        resp.raise_for_status()
        logger.info("Database connection verified via REST API")
        return cls

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.aclose()
            cls._client = None

    @classmethod
    async def execute(cls, query, *args):
        sql_upper = query.strip().upper()
        if sql_upper.startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP")):
            return await cls._call_dml(query, args)
        else:
            return await cls._call_rpc(query, args)

    @classmethod
    async def fetchrow(cls, query, *args):
        rows = await cls._call_rpc(query, args)
        return rows[0] if rows else None

    @classmethod
    async def fetch(cls, query, *args):
        return await cls._call_rpc(query, args)

    @classmethod
    async def fetchval(cls, query, *args):
        rows = await cls._call_rpc(query, args)
        if rows and isinstance(rows[0], dict):
            return next(iter(rows[0].values()), None)
        return None

    @classmethod
    async def run_migrations(cls):
        """Migrations already applied via management API."""
        logger.info("Migrations managed externally - skipping")
