"""Database connection — Supabase REST API or direct PostgreSQL."""
import os
import logging
import json
from typing import Any, Optional, List
import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = ""
SUPABASE_KEY = ""
DATABASE_URL = ""
HEADERS = {}

def init_db():
    """Initialize DB connection from environment."""
    global SUPABASE_URL, SUPABASE_KEY, DATABASE_URL, HEADERS
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    
    if SUPABASE_URL and SUPABASE_KEY:
        HEADERS = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        logger.info("Using Supabase REST API")
    elif DATABASE_URL:
        host = DATABASE_URL.split("@")[1].split("/")[0] if "@" in DATABASE_URL else "unknown"
        logger.info(f"Using direct PostgreSQL via DATABASE_URL (host: {host})")
    else:
        logger.error("No database configuration found!")

def _use_rest():
    return bool(SUPABASE_URL and SUPABASE_KEY)

# -- REST API methods --

async def table_select(table, columns="*", filters=None, order=None, limit=None, single=False):
    """SELECT from table."""
    if _use_rest():
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
            if resp.status_code == 406 and single:
                return None
            if resp.status_code >= 400:
                logger.error(f"Select error on {table}: {resp.status_code} {resp.text}")
                return [] if not single else None
            return resp.json()
    else:
        where = ""
        args = []
        if filters:
            clauses = [f"{k} = ${i+1}" for i, k in enumerate(filters.keys())]
            where = " WHERE " + " AND ".join(clauses)
            args = list(filters.values())
        query = f"SELECT {columns} FROM {table}{where}"
        if order:
            query += f" ORDER BY {order.replace('.', ' ')}"
        if limit:
            query += f" LIMIT {limit}"
        rows = await _pg_fetch(query, args)
        if single:
            return rows[0] if rows else None
        return rows or []

async def table_insert(table, data, upsert=False):
    """INSERT into table."""
    if _use_rest():
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = {**HEADERS}
        if upsert:
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=data)
            if resp.status_code >= 400:
                logger.error(f"Insert error on {table}: {resp.status_code} {resp.text}")
                return None
            try:
                result = resp.json()
                return result[0] if isinstance(result, list) and result else result
            except Exception:
                return None
    else:
        cols = list(data.keys())
        vals = list(data.values())
        placeholders = [f"${i+1}" for i in range(len(cols))]
        conflict = " ON CONFLICT DO NOTHING" if upsert else ""
        query = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)}){conflict} RETURNING *"
        rows = await _pg_fetch(query, vals)
        return rows[0] if rows else None

async def table_update(table, data, filters):
    """UPDATE table."""
    if _use_rest():
        url = f"{SUPABASE_URL}/rest/v1/{table}?"
        params = [f"{k}=eq.{v}" for k, v in filters.items()]
        url += "&".join(params)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.patch(url, headers=HEADERS, json=data)
            if resp.status_code >= 400:
                logger.error(f"Update error on {table}: {resp.status_code} {resp.text}")
                return None
            try:
                result = resp.json()
                return result[0] if isinstance(result, list) and result else result
            except Exception:
                return None
    else:
        set_clauses = [f"{k} = ${i+1}" for i, k in enumerate(data.keys())]
        offset = len(data)
        where_clauses = [f"{k} = ${i+offset+1}" for i, k in enumerate(filters.keys())]
        query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)} RETURNING *"
        args = list(data.values()) + list(filters.values())
        rows = await _pg_fetch(query, args)
        return rows[0] if rows else None

async def table_delete(table, filters):
    """DELETE from table."""
    if _use_rest():
        url = f"{SUPABASE_URL}/rest/v1/{table}?"
        params = [f"{k}=eq.{v}" for k, v in filters.items()]
        url += "&".join(params)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(url, headers=HEADERS)
            if resp.status_code >= 400:
                logger.error(f"Delete error on {table}: {resp.status_code} {resp.text}")
                return False
            return True
    else:
        clauses = [f"{k} = ${i+1}" for i, k in enumerate(filters.keys())]        
        query = f"DELETE FROM {table} WHERE {' AND '.join(clauses)}"
        await _pg_execute(query, list(filters.values()))
        return True

async def rpc(function_name, params=None):
    """Call RPC function."""
    if _use_rest():
        url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=HEADERS, json=params or {})
            if resp.status_code >= 400:
                logger.error(f"RPC error {function_name}: {resp.status_code} {resp.text}")
                return None
            try:
                return resp.json()
            except Exception:
                return resp.text
    return None

# -- Direct PostgreSQL via asyncpg --

_pool = None

async def _get_pool():
    global _pool
    if _pool is None:
        import asyncpg
        import ssl
        from urllib.parse import urlparse, unquote
        
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        # Parse DATABASE_URL manually to handle dots in username
        parsed = urlparse(DATABASE_URL)
        user = unquote(parsed.username or "")
        password = unquote(parsed.password or "")
        host = parsed.hostname or ""
        port = parsed.port or 5432
        database = (parsed.path or "/postgres").lstrip("/")
        
        logger.info(f"Connecting to PG: user={user}, host={host}, port={port}, db={database}")
        
        try:
            _pool = await asyncpg.create_pool(
                user=user,
                password=password,
                host=host,
                port=port,
                database=database,
                min_size=1,
                max_size=3,
                ssl=ssl_ctx,
                command_timeout=30,
                statement_cache_size=0,  # Required for transaction pooler
            )
            logger.info("PostgreSQL pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create PG pool: {e}")
            raise
    return _pool

async def _pg_fetch(query, args=None):
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *(args or []))
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"PG fetch error: {e}")
        return []

async def _pg_execute(query, args=None):
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await conn.execute(query, *(args or []))
    except Exception as e:
        logger.error(f"PG execute error: {e}")
