"""Async PostgreSQL connection pool."""
import asyncio
import logging
import ssl as ssl_module
import asyncpg
from config import Config

logger = logging.getLogger(__name__)

class Database:
    _pool = None

    @classmethod
    async def get_pool(cls):
        if cls._pool is None or cls._pool._closed:
            ssl_ctx = ssl_module.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl_module.CERT_NONE
            dsn = Config.DATABASE_URL
            if '?' not in dsn:
                dsn += '?sslmode=require'
            elif 'sslmode' not in dsn:
                dsn += '&sslmode=require'
            try:
                cls._pool = await asyncpg.create_pool(
                    dsn, min_size=1, max_size=5,
                    command_timeout=60, statement_cache_size=0,
                    ssl=ssl_ctx,
                )
                logger.info("Database pool created")
            except Exception as e:
                logger.error(f"Database pool creation failed: {e}")
                try:
                    cls._pool = await asyncpg.create_pool(
                        Config.DATABASE_URL, min_size=1, max_size=5,
                        command_timeout=60, statement_cache_size=0,
                    )
                    logger.info("Database pool created (no SSL)")
                except Exception as e2:
                    logger.error(f"Database pool creation failed (no SSL): {e2}")
                    raise
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
