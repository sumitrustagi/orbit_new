"""
Route decorators for role-based access control and audit logging.
"""
import functools
from typing import Callable

from flask import abort, request, jsonify
from flask_login import current_user


def superadmin_required(fn: Callable) -> Callable:
    """Restrict access to platform_admin users only."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role.value != "platform_admin":
            if request.is_json:
                return jsonify({"error": "Platform admin access required."}), 403
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def gui_admin_required(fn: Callable) -> Callable:
    """Restrict access to gui_admin or platform_admin users."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role.value not in ("platform_admin", "gui_admin"):
            if request.is_json:
                return jsonify({"error": "Admin access required."}), 403
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn: Callable) -> Callable:
    """Alias for gui_admin_required."""
    return gui_admin_required(fn)


def _get_ip() -> str:
    """
    Extract the real client IP, respecting X-Forwarded-For
    behind a reverse proxy.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"
