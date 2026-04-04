"""Supabase REST API connection layer."""
import logging
import aiohttp
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


async def supabase_request(method, table, params=None, json_data=None, single=False):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        query_parts = [f"{k}={v}" for k, v in params.items()]
        if query_parts:
            url += "?" + "&".join(query_parts)
    headers = dict(HEADERS)
    headers["Accept"] = "application/vnd.pgrst.object+json" if single else "application/json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=json_data, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status in (404, 406):
                    return None
                if resp.status >= 400:
                    text = await resp.text()
                    logger.error(f"Supabase {method} {table}: {resp.status} {text[:200]}")
                    return None if single else []
                if resp.status == 204:
                    return None if single else []
                return await resp.json()
    except Exception as e:
        logger.error(f"Supabase error: {e}")
        return None if single else []


async def sb_select(table, params=None, single=False):
    return await supabase_request("GET", table, params=params, single=single)

async def sb_insert(table, data, single=True):
    result = await supabase_request("POST", table, json_data=data)
    if single and isinstance(result, list) and result:
        return result[0]
    return result

async def sb_update(table, params, data, single=True):
    result = await supabase_request("PATCH", table, params=params, json_data=data)
    if single and isinstance(result, list) and result:
        return result[0]
    return result

async def sb_upsert(table, data, single=True):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = dict(HEADERS)
    headers["Prefer"] = "return=representation,resolution=merge-duplicates"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    logger.error(f"Supabase upsert {table}: {resp.status} {text[:200]}")
                    return None
                result = await resp.json()
                if single and isinstance(result, list) and result:
                    return result[0]
                return result
    except Exception as e:
        logger.error(f"Supabase upsert error: {e}")
        return None

async def sb_delete(table, params):
    return await supabase_request("DELETE", table, params=params)
