"""Audit log routes."""
from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models.audit import AuditLog
from app.utils.decorators import gui_admin_required

audit_bp = Blueprint("audit", __name__, url_prefix="/audit", template_folder="../templates/audit")


@audit_bp.route("/")
@login_required
@gui_admin_required
def list_logs():
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category", "").strip()
    action = request.args.get("action", "").strip()
    username = request.args.get("username", "").strip()

    query = AuditLog.query
    if category:
        query = query.filter(AuditLog.category == category)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))

    logs = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50, error_out=False)

    categories = ["auth", "cucm", "unity", "imp", "expressway", "system"]
    return render_template("list.html", logs=logs, categories=categories,
                           filter_category=category, filter_action=action, filter_username=username)
