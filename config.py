"""Application configuration from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "Botofall_robot")
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
    SUPERADMIN_IDS = [int(x.strip()) for x in os.getenv("SUPERADMIN_IDS", "").split(",") if x.strip().isdigit()]
    PORT = int(os.getenv("PORT", "10000"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", "30"))
    RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))
    PREMIUM_ENABLED = os.getenv("PREMIUM_ENABLED", "false").lower() == "true"
    PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")
    PREMIUM_PRICE_MONTHLY = int(os.getenv("PREMIUM_PRICE_MONTHLY", "199"))
    BUSINESS_PRICE_MONTHLY = int(os.getenv("BUSINESS_PRICE_MONTHLY", "499"))
    MAX_CHANNELS_FREE = int(os.getenv("MAX_CHANNELS_FREE", "3"))
    MAX_CHANNELS_PREMIUM = int(os.getenv("MAX_CHANNELS_PREMIUM", "20"))
    DRIP_INTERVAL_HOURS = int(os.getenv("DRIP_INTERVAL_HOURS", "24"))
    CLONE_ENABLED = os.getenv("CLONE_ENABLED", "true").lower() == "true"

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        return True
