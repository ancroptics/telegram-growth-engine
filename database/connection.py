"""Async PostgreSQL connection via Supabase REST API (HTTPS).

Uses the PostgREST RPC endpoint to execute raw SQL,
and Supabase client for ORM-style queries.
"""
import os
import logging
import json
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ── Supabase connection info (from env) ──────────────────────────
SUPABASE_URL: str = ""
SUPABASE_KEY: str = ""
HEADERS: dict = {}

_supabase_client = None


def init_db():
    """Initialize DB connection settings from environment variables."""
    global SUPABASE_URL, SUPABASE_KEY, HEADERS, _supabase_client
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY not set!")
        return
    HEADERS = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized")
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")


def get_supabase():
    """Return the Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        init_db()
    return _supabase_client


async def execute_sql(query: str, params: Optional[dict] = None) -> Any:
    """Execute raw SQL via Supabase RPC."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    payload = {"query": query}
    if params:
        payload["params"] = params
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=HEADERS, json=payload)
        if resp.status_code >= 400:
            logger.error(f"SQL error: {resp.status_code} {resp.text}")
            return None
        try:
            return resp.json()
        except Exception:
            return resp.text


async def table_select(
    table: str,
    columns: str = "*",
    filters: Optional[dict] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
    single: bool = False,
) -> Any:
    """SELECT from a Supabase table via REST."""
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


async def table_insert(table: str, data: dict, upsert: bool = False) -> Any:
    """INSERT into a Supabase table."""
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


async def table_update(table: str, data: dict, filters: dict) -> Any:
    """UPDATE a Supabase table row."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    for k, v in filters.items():
        url += f"?{k}=eq.{v}"
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


async def table_delete(table: str, filters: dict) -> bool:
    """DELETE from a Supabase table."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    for k, v in filters.items():
        url += f"?{k}=eq.{v}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(url, headers=HEADERS)
        if resp.status_code >= 400:
            logger.error(f"Delete error on {table}: {resp.status_code} {resp.text}")
            return False
        return True


async def rpc(function_name: str, params: Optional[dict] = None) -> Any:
    """Call a Supabase RPC function."""
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
