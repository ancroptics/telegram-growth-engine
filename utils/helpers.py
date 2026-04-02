"""Formatting and variable replacement utilities."""
from datetime import datetime

def format_number(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)

def progress_bar(current: int, total: int, length: int = 10) -> str:
    if total == 0: return "░" * length
    filled = int(length * current / total)
    return "█" * filled + "░" * (length - filled)

def replace_variables(text: str, user=None, channel=None, extra: dict = None) -> str:
    if not text: return ""
    replacements = {}
    if user:
        replacements["{first_name}"] = user.first_name or ""
        replacements["{last_name}"] = user.last_name or ""
        replacements["{full_name}"] = user.full_name or ""
        replacements["{username}"] = f"@{user.username}" if user.username else ""
        replacements["{user_id}"] = str(user.id)
    if channel:
        replacements["{channel_name}"] = channel.get("chat_title", "")
        replacements["{channel_id}"] = str(channel.get("chat_id", ""))
        replacements["{member_count}"] = format_number(channel.get("member_count", 0))
    replacements["{date}"] = datetime.now().strftime("%Y-%m-%d")
    if extra:
        replacements.update(extra)
    for key, val in replacements.items():
        text = text.replace(key, str(val))
    return text

def truncate(text: str, max_len: int = 4096) -> str:
    if len(text) <= max_len: return text
    return text[:max_len - 3] + "..."
