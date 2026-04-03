"""Configuration for the Telegram Growth Engine bot."""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """Bot configuration from environment variables."""
    # Telegram
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
    WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "tge_secret_token_2024")
    WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")

    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

    # Admin IDs
    ADMIN_IDS = []
    SUPERADMIN_IDS = []

    _raw_admins = os.environ.get("ADMIN_IDS", "")
    _raw_superadmins = os.environ.get("SUPERADMIN_IDS", "")
    if _raw_admins:
        try:
            ADMIN_IDS = [int(x.strip()) for x in _raw_admins.split(",") if x.strip()]
        except ValueError:
            logger.warning(f"Invalid ADMIN_IDS: {_raw_admins}")
    if _raw_superadmins:
        try:
            SUPERADMIN_IDS = [int(x.strip()) for x in _raw_superadmins.split(",") if x.strip()]
        except ValueError:
            logger.warning(f"Invalid SUPERADMIN_IDS: {_raw_superadmins}")

    # Server
    PORT = int(os.environ.get("PORT", "10000"))
    HOST = os.environ.get("HOST", "0.0.0.0")
    HEALTH_CHECK_PATH = os.environ.get("HEALTH_CHECK_PATH", "/health")

    # Features
    DEFAULT_TIER = os.environ.get("DEFAULT_TIER", "free")
    MAX_CHANNELS_FREE = int(os.environ.get("MAX_CHANNELS_FREE", "3"))
    MAX_CHANNELS_PREMIUM = int(os.environ.get("MAX_CHANNELS_PREMIUM", "10"))
    MAX_CHANNELS_BUSINESS = int(os.environ.get("MAX_CHANNELS_BUSINESS", "50"))

    @classmethod
    def validate(cls) -> bool:
        """Validate required config."""
        missing = []
        if not cls.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if not cls.DATABASE_URL and not cls.SUPABASE_URL:
            missing.append("DATABASE_URL or SUPABASE_URL")
        if missing:
            logger.error(f"Missing required env vars: {', '.join(missing)}")
            return False
        return True
