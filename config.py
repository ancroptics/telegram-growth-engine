"""Environment-driven configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    SUPERADMIN_IDS = [int(x.strip()) for x in os.getenv("SUPERADMIN_IDS", "0").split(",") if x.strip().isdigit()]
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
    PORT = int(os.getenv("PORT", "10000"))
    USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    BOT_USERNAME = ""
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DEFAULT_REFERRAL_COINS = int(os.getenv("DEFAULT_REFERRAL_COINS", "10"))
    DEFAULT_APPROVE_RATE = int(os.getenv("DEFAULT_APPROVE_RATE", "20"))
    PREMIUM_PRICE_MONTHLY = int(os.getenv("PREMIUM_PRICE_MONTHLY", "199"))
    BUSINESS_PRICE_MONTHLY = int(os.getenv("BUSINESS_PRICE_MONTHLY", "499"))
    MAX_BROADCAST_RATE = 25
