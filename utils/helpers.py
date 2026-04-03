"""Utility helper functions."""
from html import escape as html_escape


def replace_variables(text: str, user=None, channel=None) -> str:
    """Replace template variables in text."""
    if not text:
        return text
    if user:
        text = text.replace("{first_name}", html_escape(getattr(user, "first_name", "") or ""))
        text = text.replace("{last_name}", html_escape(getattr(user, "last_name", "") or ""))
        text = text.replace("{username}", getattr(user, "username", "") or "")
        text = text.replace("{user_id}", str(getattr(user, "id", "")))
        text = text.replace("{full_name}", html_escape(getattr(user, "full_name", "") or ""))
    if channel:
        text = text.replace("{channel_title}", html_escape(channel.get("chat_title", "")))
        text = text.replace("{channel_id}", str(channel.get("chat_id", "")))
    return text
