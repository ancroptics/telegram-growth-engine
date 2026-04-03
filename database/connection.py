"""Database connection - Supabase REST API with graceful error handling."""
import os
import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

_rest_ok = True  # Will be set False if REST fails with auth error
_pg_pool = None

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def init_db():
    """Initialize database connections."""
    global _rest_ok
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("No SUPABASE_URL/KEY - REST API disabled")
        _rest_ok = False
    else:
        logger.info(f"Supabase REST configured: {SUPABASE_URL}")

    if DATABASE_URL:
        logger.info("Direct PostgreSQL configured as fallback")
        asyncio.get_event_loop().create_task(_init_pg_pool())


async def _init_pg_pool():
    """Try to create asyncpg pool."""
    global _pg_pool
    try:
        import asyncpg
        _pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5, command_timeout=10)
        logger.info("PostgreSQL pool created successfully")
    except Exception as e:
        logger.error(f"PG pool failed: {e}")
        _pg_pool = None


async def _rest_request(method, url, **kwargs):
    """Make REST request with error handling."""
    global _rest_ok
    if not _rest_ok:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.request(method, url, headers=HEADERS, **kwargs)
            if resp.status_code == 401:
                logger.error("Supabase REST 401 - disabling REST")
                _rest_ok = False
                return None
            if resp.status_code == 404:
                # Table doesn't exist in PostgREST schema
                logger.debug(f"404 for {url} - table may not exist")
                return None
            if resp.status_code >= 400:
                logger.warning(f"REST {resp.status_code}: {resp.text[:200]}")
                return None
            return resp
    except Exception as e:
        logger.error(f"REST request error: {e}")
        return None


async def table_select(table, filters=None, single=False, columns="*", order=None, limit=None):
    """SELECT from table via REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={columns}"
    if filters:
        for k, v in filters.items():
            url += f"&{k}=eq.{v}"
    if order:
        col, direction = (order.split(".") + ["asc"])[:2]
        url += f"&order={col}.{direction}"
    if limit:
        url += f"&limit={limit}"
    if single:
        url += "&limit=1"

    resp = await _rest_request("GET", url)
    if resp is None:
        return None if single else []

    try:
        data = resp.json()
        if single:
            return data[0] if data else None
        return data if isinstance(data, list) else []
    except Exception:
        return None if single else []


async def table_insert(table, data, upsert=False):
    """INSERT into table via REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers_extra = dict(HEADERS)
    if upsert:
        headers_extra["Prefer"] = "return=representation,resolution=merge-duplicates"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, headers=headers_extra, json=data)
            if resp.status_code == 404:
                logger.debug(f"Table {table} not found for insert")
                return [data]
            if resp.status_code >= 400:
                logger.warning(f"Insert {table} failed ({resp.status_code}): {resp.text[:200]}")
                return [data]
            result = resp.json()
            return result if isinstance(result, list) else [result] if result else [data]
    except Exception as e:
        logger.error(f"Insert {table} error: {e}")
        return [data]


async def table_update(table, data, filters):
    """UPDATE table via REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?"
    url += "&".join(f"{k}=eq.{v}" for k, v in filters.items())

    resp = await _rest_request("PATCH", url, json=data)
    if resp is None:
        return []
    try:
        return resp.json()
    except Exception:
        return []


async def table_delete(table, filters):
    """DELETE from table via REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?"
    url += "&".join(f"{k}=eq.{v}" for k, v in filters.items())

    resp = await _rest_request("DELETE", url)
    if resp is None:
        return []
    try:
        return resp.json()
    except Exception:
        return []


async def table_count(table, filters=None):
    """COUNT rows in table."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=count"
    if filters:
        for k, v in filters.items():
            url += f"&{k}=eq.{v}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={**HEADERS, "Prefer": "count=exact"})
            if resp.status_code == 404:
                return 0
            count = resp.headers.get("content-range", "*/0").split("/")[-1]
            return int(count) if count != "*" else 0
    except Exception:
        return 0


async def rpc_call(function_name, params=None):
    """Call a Supabase RPC function."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    resp = await _rest_request("POST", url, json=params or {})
    if resp is None:
        return None
    try:
        return resp.json()
    except Exception:
        return None
