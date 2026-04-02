"""Async PostgreSQL connection pool."""
import asyncio
import logging
import socket
import ssl as ssl_module
from urllib.parse import urlparse, urlunparse
import asyncpg
from config import Config

logger = logging.getLogger(__name__)


def _resolve_ipv4(hostname: str) -> str:
    """Resolve hostname to IPv4 address to avoid IPv6 routing issues."""
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        if results:
            ip = results[0][4][0]
            logger.info(f"Resolved {hostname} -> {ip} (IPv4)")
            return ip
    except socket.gaierror as e:
        logger.warning(f"IPv4 resolution failed for {hostname}: {e}")
    return hostname


def _dsn_with_ipv4(dsn: str) -> tuple[str, str]:
    """Replace hostname in DSN with IPv4 address. Returns (new_dsn, original_host)."""
    parsed = urlparse(dsn)
    original_host = parsed.hostname
    ipv4 = _resolve_ipv4(original_host)
    if ipv4 != original_host:
        # Replace host in netloc
        if parsed.port:
            new_netloc = f"{parsed.username}:{parsed.password}@{ipv4}:{parsed.port}"
        else:
            new_netloc = f"{parsed.username}:{parsed.password}@{ipv4}"
        new_dsn = urlunparse(parsed._replace(netloc=new_netloc))
        return new_dsn, original_host
    return dsn, original_host


class Database:
    _pool = None

    @classmethod
    async def get_pool(cls):
        if cls._pool is None or cls._pool._closed:
            ssl_ctx = ssl_module.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl_module.CERT_NONE

            dsn = Config.DATABASE_URL
            # Try IPv4-resolved DSN first, then original
            ipv4_dsn, original_host = _dsn_with_ipv4(dsn)

            for attempt_dsn, label in [(ipv4_dsn, "IPv4"), (dsn, "original")]:
                try:
                    cls._pool = await asyncpg.create_pool(
                        attempt_dsn, min_size=1, max_size=5,
                        command_timeout=60, statement_cache_size=0,
                        ssl=ssl_ctx,
                    )
                    logger.info(f"Database pool created ({label})")
                    return cls._pool
                except Exception as e:
                    logger.error(f"Database pool creation failed ({label}): {e}")

            # Final fallback: no SSL
            for attempt_dsn, label in [(ipv4_dsn, "IPv4 no-SSL"), (dsn, "original no-SSL")]:
                try:
                    cls._pool = await asyncpg.create_pool(
                        attempt_dsn, min_size=1, max_size=5,
                        command_timeout=60, statement_cache_size=0,
                    )
                    logger.info(f"Database pool created ({label})")
                    return cls._pool
                except Exception as e:
                    logger.error(f"Database pool creation failed ({label}): {e}")

            raise RuntimeError("All database connection attempts failed")
        return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()

    @classmethod
    async def execute(cls, query, *args):
        pool = await cls.get_pool()
        return await pool.execute(query, *args)

    @classmethod
    async def fetchrow(cls, query, *args):
        pool = await cls.get_pool()
        return await pool.fetchrow(query, *args)

    @classmethod
    async def fetch(cls, query, *args):
        pool = await cls.get_pool()
        return await pool.fetch(query, *args)

    @classmethod
    async def fetchval(cls, query, *args):
        pool = await cls.get_pool()
        return await pool.fetchval(query, *args)

    @classmethod
    async def run_migrations(cls):
        pool = await cls.get_pool()
        import os
        migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if not os.path.exists(migration_dir):
            return
        for fname in sorted(os.listdir(migration_dir)):
            if fname.endswith(".sql"):
                path = os.path.join(migration_dir, fname)
                with open(path) as f:
                    sql = f.read()
                try:
                    await pool.execute(sql)
                    logger.info(f"Migration {fname} applied")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        logger.info(f"Migration {fname} already applied")
                    else:
                        logger.error(f"Migration {fname} failed: {e}")
