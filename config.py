"""Bot configuration."""
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")
PORT = int(os.getenv("PORT", "10000"))

_admin_str = os.getenv("ADMIN_IDS", "") or os.getenv("SUPERADMIN_IDS", "")
ADMIN_IDS = set()
for x in _admin_str.split(","):
    x = x.strip()
    if x.isdigit():
        ADMIN_IDS.add(int(x))
