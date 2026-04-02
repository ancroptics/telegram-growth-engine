"""Language service for multi-language welcome messages."""
import json

def get_welcome_for_language(channel: dict, user_language: str = None) -> str:
    default = channel.get("welcome_message", "Welcome to {channel_name}!")
    if not user_language:
        return default
    i18n = channel.get("welcome_messages_i18n") or {}
    if isinstance(i18n, str):
        i18n = json.loads(i18n)
    if user_language in i18n:
        return i18n[user_language]
    base = user_language.split("-")[0]
    return i18n.get(base, default)
