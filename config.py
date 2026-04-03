"""Bot configuration from environment variables."""
import os

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    SUPERADMIN_IDS = [
        int(x.strip()) for x in os.getenv("SUPERADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    ]
    PORT = int(os.getenv("PORT", "10000"))
    USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    DEFAULT_REFERRAL_COINS = int(os.getenv("DEFAULT_REFERRAL_COINS", "10"))
    PREMIUM_PRICE_MONTHLY = int(os.getenv("PREMIUM_PRICE_MONTHLY", "199"))
    BUSINESS_PRICE_MONTHLY = int(os.getenv("BUSINESS_PRICE_MONTHLY", "499"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Rate limiting
    RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "30"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Clone settings
    MAX_CLONES_FREE = int(os.getenv("MAX_CLONES_FREE", "1"))
    MAX_CLONES_PREMIUM = int(os.getenv("MAX_CLONES_PREMIUM", "5"))
    MAX_CLONES_BUSINESS = int(os.getenv("MAX_CLONES_BUSINESS", "20"))

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        return True
