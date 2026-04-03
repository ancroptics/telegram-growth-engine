"""Health check HTTP server for Render + UptimeRobot."""
import logging
from aiohttp import web
from config import Config

logger = logging.getLogger(__name__)
VERSION = "v3.0.0"

async def health_check(request):
    from database.connection import Database
    db_ok = False
    try:
        val = await Database.fetchval("SELECT 1")
        db_ok = val == 1
    except Exception:
        pass
    return web.json_response({"status": "running", "db": db_ok, "bot_username": Config.BOT_USERNAME, "version": VERSION})

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
    await site.start()
    logger.info(f"Health server running on port {Config.PORT}")
    return runner
