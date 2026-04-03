"""Application configuration from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "Botofall_robot")

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "telegram_growth")

    # Admin
    ADMIN_IDS = [
        int(x.strip())
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    ]
    SUPER_ADMIN_IDS = [
        int(x.strip())
        for x in os.getenv("SUPEP_ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    ]

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # Rate Limiting
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", "30"))
    RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))

    # Premium
    PREMIUM_ENABLED = os.getenv("PREMIUM_ENABLED", "false").lower() == "true"
    PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")

    # Feature Flags
    MAX_CHANNELS_FREE = int(os.getenv("MAX_CHANNELS_FREE", "3"))
    MAX_CHANNELS_PREMIUM = int(os.getenv("MAX_CHANNELS_PREMIUM", "20"))
    DRIP_INTERVAL_HOURS = int(os.getenv("DRIP_INTERVAL_HOURS", "24"))
    CLONE_ENABLED = os.getenv("CLONE_ENABLED", "true").lower() == "true"

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not cls.MONGO_URI:
            raise ValueError("MONGO_URI is required")
        return True
