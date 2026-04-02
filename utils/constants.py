"""Constants and tier limits."""

TIER_LIMITS = {
    "free": {"max_channels": 1, "max_clones": 0, "analytics_days": 7, "media_dm": False, "force_sub": False, "drip": False, "cross_promo": False, "auto_poster": False, "export": False, "watermark": True},
    "premium": {"max_channels": 5, "max_clones": 1, "analytics_days": 30, "media_dm": True, "force_sub": True, "drip": True, "cross_promo": True, "auto_poster": False, "export": True, "watermark": False},
    "business": {"max_channels": 999, "max_clones": 5, "analytics_days": 90, "media_dm": True, "force_sub": True, "drip": True, "cross_promo": True, "auto_poster": True, "export": True, "watermark": False},
}

TIER_EMOJI = {"free": "🆓", "premium": "💎", "business": "💼"}

CATEGORIES = ["Tech", "Entertainment", "Education", "News", "Crypto", "Finance", "Gaming", "Music", "Sports", "Health", "Travel", "Food", "Fashion", "Art", "Science", "Other"]

WELCOME_VARIABLES = {
    "{first_name}": "User first name",
    "{last_name}": "User last name",
    "{full_name}": "User full name",
    "{username}": "User @username",
    "{user_id}": "User ID",
    "{channel_name}": "Channel title",
    "{channel_id}": "Channel ID",
    "{member_count}": "Channel member count",
    "{date}": "Current date",
    "{referral_link}": "User referral link",
}
