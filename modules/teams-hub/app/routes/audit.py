"""
Audit Log Blueprint.

Routes:
  GET /admin/audit/     → Paginated audit log viewer
  GET /admin/audit/api  → JSON audit log endpoint
"""
import logging

from flask import (
    Blueprint, render_template, request, jsonify,
)
from flask_login import login_required

from app.utils.decorators import superadmin_required
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

audit_bp = Blueprint(
    "audit", __name__,
    template_folder="../templates/audit",
    url_prefix="/admin/audit",
)


@audit_bp.route("/", methods=["GET"])
@login_required
@superadmin_required
def list_logs():
    """Paginated audit log viewer."""
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 50
    action   = request.args.get("action", "").strip()
    username = request.args.get("username", "").strip()

    q = AuditLog.query

    if action:
        q = q.filter(AuditLog.action == action)
    if username:
        q = q.filter(AuditLog.username.ilike(f"%{username}%"))

    q     = q.order_by(AuditLog.timestamp.desc())
    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    # Distinct actions for filter dropdown
    actions = [
        r[0] for r in
        AuditLog.query.with_entities(AuditLog.action)
        .distinct()
        .order_by(AuditLog.action.asc())
        .all()
    ]

    return render_template(
        "list.html",
        items=items,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        action=action,
        username_filter=username,
        actions=actions,
    )


@audit_bp.route("/api", methods=["GET"])
@login_required
@superadmin_required
def api_logs():
    """JSON audit log endpoint for AJAX."""
    limit = min(100, int(request.args.get("limit", 30)))
    logs = (
        AuditLog.query
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return jsonify([log.to_dict() for log in logs])
