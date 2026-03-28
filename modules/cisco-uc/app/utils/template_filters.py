"""Custom Jinja2 template filters."""
from datetime import datetime, timezone


def timeago(dt):
    if dt is None:
        return "never"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = seconds // 60
        return f"{m}m ago"
    if seconds < 86400:
        h = seconds // 3600
        return f"{h}h ago"
    d = seconds // 86400
    return f"{d}d ago"


def datetime_format(dt, fmt="%Y-%m-%d %H:%M:%S"):
    if dt is None:
        return ""
    return dt.strftime(fmt)


def register_filters(app):
    app.jinja_env.filters["timeago"] = timeago
    app.jinja_env.filters["datetime_format"] = datetime_format
