"""
Custom Jinja2 template filters and helpers.
"""
from datetime import datetime, timezone

from flask import Flask


def register_filters(app: Flask) -> None:
    """Register all custom Jinja2 filters on the app."""

    @app.template_filter("timeago")
    def timeago_filter(dt: datetime | None) -> str:
        """Human-friendly 'time ago' string."""
        if dt is None:
            return "never"
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
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
        if d == 1:
            return "yesterday"
        if d < 30:
            return f"{d}d ago"
        if d < 365:
            months = d // 30
            return f"{months}mo ago"
        years = d // 365
        return f"{years}y ago"

    @app.template_filter("fmt_dt")
    def format_datetime(dt: datetime | None, fmt: str = "%d %b %Y %H:%M") -> str:
        """Format a datetime for display."""
        if dt is None:
            return "—"
        return dt.strftime(fmt)

    @app.template_filter("truncate_id")
    def truncate_id(value: str, length: int = 8) -> str:
        """Truncate a long ID string for display."""
        if not value:
            return ""
        return value[:length] + "…" if len(value) > length else value
