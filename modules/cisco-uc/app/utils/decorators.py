"""Access-control decorators."""
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def login_required_with_message(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def platform_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_platform_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def gui_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_gui_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _get_ip():
    """Get client IP, handling reverse proxies."""
    from flask import request
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"
