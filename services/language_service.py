"""Language/i18n service for welcome messages."""
import json
import logging

logger = logging.getLogger(__name__)


def get_welcome_for_language(channel: dict, lang_code: str = None) -> str:
    """Get welcome message for user language, fallback to default."""
    i18n = channel.get("welcome_messages_i18n")
    if not i18n:
        return channel.get("welcome_message", "")
    if isinstance(i18n, str):
        try:
            i18n = json.loads(i18n)
        except Exception:
            return channel.get("welcome_message", "")
    if isinstance(i18n, dict):
        if lang_code and lang_code in i18n:
            return i18n[lang_code]
        return i18n.get("en", i18n.get("default", channel.get("welcome_message", "")))
    return channel.get("welcome_message", "")
