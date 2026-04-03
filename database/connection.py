"""Database connection - Supabase REST API or direct PostgreSQL."""
import os
import logging
import json
import time
from typing import Any, Optional, List
import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = ""
SUPABASE_KEY = ""
DATABASE_URL = ""
HEADERS = {}
_rest_disabled = False
_pool = None
_pool_failed = False
_last_db_error_time = 0

def init_db():
    global SUPABASE_URL, SUPABASE_KEY, DATABASE_URL, HEADERS
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    if SUPABASE_URL and SUPABASE_KEY:
        HEADERS = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        logger.info("Supabase REST API configured")
    if DATABASE_URL:
        logger.info("Direct PostgreSQL configured as fallback")
    if not SUPABASE_URL and not DATABASE_URL:
        logger.warning("No database config - bot runs in degraded mode")

def _use_rest():
    return bool(SUPABASE_URL and SUPABASE_KEY and not _rest_disabled)

def _disable_rest(reason=""):
    global _rest_disabled
    if not _rest_disabled:
        _rest_disabled = True
        logger.warning(f"REST API disabled, falling back to direct PG. Reason: {reason}")

async def table_select(table, columns="*", filters=None, order=None, limit=None, single=False):
    if _use_rest():
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table}?select={columns}"
            if filters:
                for k, v in filters.items():
                    url += f"&{k}=eq.{v}"
            if order:
                url += f"&order={order}"
            if limit:
                url += f"&limit={limit}"
            headers = {**HEADERS}
            if single:
                headers["Accept"] = "application/vnd.pgrst.object+json"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 401:
                    _disable_rest("got 401 Unauthorized")
                    return await table_select(table, columns, filters, order, limit, single)
                if resp.status_code == 406 and single:
                    return None
                if resp.status_code >= 400:
                    logger.error(f"REST select {table}: HTTP {resp.status_code}")
                    return [] if not single else None
                return resp.json()
        except Exception as e:
            logger.error(f"REST select {table}: {e}")
            if DATABASE_URL:
                _disable_rest(str(e))
                return await table_select(table, columns, filters, order, limit, single)
            return [] if not single else None

    if DATABASE_URL:
        where, args = "", []
        if filters:
            clauses = [f"{k} = ${i+1}" for i, k in enumerate(filters.keys())]
            where = " WHERE " + " AND ".join(clauses)
            args = list(filters.values())
        q = f"SELECT {columns} FROM {table}{where}"
        if order:
            q += f" ORDER BY {order.replace(".", " ")}"
        if limit:
            q += f" LIMIT {limit}"
        rows = await _pg_fetch(q, args)
        return (rows[0] if rows else None) if single else (rows or [])
    return [] if not single else None

async def table_insert(table, data, upsert=False):
    if _use_rest():
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table}"
            headers = {**HEADERS}
            if upsert:
                headers["Prefer"] = "resolution=merge-duplicates,return=representation"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, headers=headers, json=data)
                if resp.status_code == 401:
                    _disable_rest("got 401 Unauthorized")
                    return await table_insert(table, data, upsert)
                if resp.status_code >= 400:
                    return None
                result = resp.json()
                return result[0] if isinstance(result, list) and result else result
        except Exception:
            if DATABASE_URL:
                _disable_rest("exception")
                return await table_insert(table, data, upsert)
            return None

    if DATABASE_URL:
        cols = list(data.keys())
        vals = list(data.values())
        ph = [f"${i+1}" for i in range(len(cols))]
        conflict = " ON CONFLICT DO NOTHING" if upsert else ""
        q = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(ph)}){conflict} RETURNING *"
        rows = await _pg_fetch(q, vals)
        return rows[0] if rows else None
    return None

async def table_update(table, data, filters):
    if _use_rest():
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table}?"
            url += "&".join(f"{k}=eq.{v}" for k, v in filters.items())
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.patch(url, headers=HEADERS, json=data)
                if resp.status_code == 401:
                    _disable_rest("got 401 Unauthorized")
                    return await table_update(table, data, filters)
                if resp.status_code >= 400:
                    return None
                result = resp.json()
                return result[0] if isinstance(result, list) and result else result
        except Exception:
            if DATABASE_URL:
                _disable_rest("exception")
                return await table_update(table, data, filters)
            return None

    if DATABASE_URL:
        sc = [f"{k} = ${i+1}" for i, k in enumerate(data.keys())]
        off = len(data)
        wc = [f"{k} = ${i+off+1}" for i, k in enumerate(filters.keys())]
        q = f"UPDATE {table} SET {', '.join(sc)} WHERE {' AND '.join(wc)} RETURNING *"
        rows = await _pg_fetch(q, list(data.values()) + list(filters.values()))
        return rows[0] if rows else None
    return None

async def table_delete(table, filters):
    if _use_rest():
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table}?"
            url += "&".join(f"{k}=eq.{v}" for k, v in filters.items())
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.delete(url, headers=HEADERS)
                if resp.status_code == 401:
                    _disable_rest("got 401 Unauthorized")
                    return await table_delete(table, filters)
                return resp.status_code < 400
        except Exception:
            if DATABASE_URL:
                _disable_rest("exception")
                return await table_delete(table, filters)
            return False

    if DATABASE_URL:
        clauses = [f"{k} = ${i+1}" for i, k in enumerate(filters.keys())]
        await _pg_execute(f"DELETE FROM {table} WHERE {' AND '.join(clauses)}", list(filters.values()))
        return True
    return False

async def rpc(function_name, params=None):
    if _use_rest():
        try:
            url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, headers=HEADERS, json=params or {})
                if resp.status_code >= 400:
                    return None
                return resp.json()
        except Exception:
            return None
    return None

# -- PostgreSQL via asyncpg --
async def _get_pool():
    global _pool, _pool_failed, _last_db_error_time
    if _pool_failed and time.time() - _last_db_error_time < 300:
        return None
    if _pool is None:
        import asyncpg, ssl
        from urllib.parse import urlparse, unquote
        _pool_failed = False
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        p = urlparse(DATABASE_URL)
        host = p.hostname
        port = p.port or 5432
        user = unquote(p.username or "")
        password = unquote(p.password or "")
        database = (p.path or "/postgres").lstrip("/")
        try:
            if host and "supabase.co" in host:
                ref = host.replace("db.", "").replace(".supabase.co", "")
                regions = ["ap-south-1", "us-east-1", "us-west-1", "eu-west-1", "ap-southeast-1"]
                for region in regions:
                    try:
                        pooler_host = f"aws-0-{region}.pooler.supabase.com"
                        _pool = await asyncpg.create_pool(
                            user=f"postgres.{ref}", password=password,
                            host=pooler_host, port=6543,
                            database=database, min_size=1, max_size=3,
                            ssl=ctx, command_timeout=30, statement_cache_size=0,
                        )
                        logger.info(f"PG pool via pooler ({region})")
                        return _pool
                    except Exception:
                        continue
                # Try direct
                _pool = await asyncpg.create_pool(
                    user=user, password=password, host=host, port=port,
                    database=database, min_size=1, max_size=3,
                    ssl=ctx, command_timeout=30, statement_cache_size=0,
                )
                logger.info("PG pool (direct)")
            else:
                _pool = await asyncpg.create_pool(
                    user=user, password=password, host=host, port=port,
                    database=database, min_size=1, max_size=3,
                    ssl=ctx, command_timeout=30, statement_cache_size=0,
                )
                logger.info("PG pool created")
        except Exception as e:
            logger.error(f"PG pool failed: {e}")
            _pool_failed = True
            _last_db_error_time = time.time()
            return None
    return _pool

async def _pg_fetch(query, args=None):
    try:
        pool = await _get_pool()
        if not pool:
            return []
        async with pool.acquire() as conn:
            return [dict(r) for r in await conn.fetch(query, *(args or []))]
    except Exception as e:
        logger.error(f"PG fetch: {e}")
        return []

async def _pg_execute(query, args=None):
    try:
        pool = await _get_pool()
        if not pool:
            return
        async with pool.acquire() as conn:
            await conn.execute(query, *(args or []))
    except Exception as e:
        logger.error(f"PG exec: {e}")
