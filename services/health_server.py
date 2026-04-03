"""Health check HTTP server for Render + UptimeRobot."""
import logging
import time
from aiohttp import web
from config import Config

logger = logging.getLogger(__name__)
VERSION = "v3.2.0"

# Bot status tracker
_bot_status = {
    "started_at": time.time(),
    "polling": False,
    "db_ok": False,
    "scheduler": False,
    "last_health_check": 0,
}

def set_bot_status(key, value):
    _bot_status[key] = value

async def health_check(request):
    from database.connection import Database
    db_ok = False
    try:
        val = await Database.fetchval("SELECT 1")
        db_ok = val == 1
    except Exception as e:
        logger.warning(f"Health check DB failed: {e}")
    
    _bot_status["last_health_check"] = time.time()
    _bot_status["db_ok"] = db_ok
    
    uptime = int(time.time() - _bot_status["started_at"])
    
    return web.json_response({
        "status": "running",
        "db": db_ok,
        "polling": _bot_status.get("polling", False),
        "scheduler": _bot_status.get("scheduler", False),
        "bot_username": Config.BOT_USERNAME,
        "version": VERSION,
        "uptime_seconds": uptime,
    })

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
