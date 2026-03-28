"""
Calls Blueprint — Call Queues & Auto Attendants.

Routes:
  GET  /admin/calls/                        → Overview
  GET  /admin/calls/queues                  → List call queues
  GET  /admin/calls/auto-attendants         → List auto attendants
  POST /admin/calls/sync                    → Sync from Graph
"""
import logging

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash,
)
from flask_login import login_required, current_user

from app.utils.decorators import gui_admin_required, _get_ip
from app.models.call_queue import CallQueue, AutoAttendant
from app.models.audit import AuditLog
from app.extensions import db

logger = logging.getLogger(__name__)

calls_bp = Blueprint(
    "calls", __name__,
    template_folder="../templates/calls",
    url_prefix="/admin/calls",
)


@calls_bp.route("/", methods=["GET"])
@login_required
def overview():
    """Call management overview."""
    stats = {
        "total_queues":      CallQueue.query.count(),
        "active_queues":     CallQueue.query.filter_by(is_active=True).count(),
        "total_attendants":  AutoAttendant.query.count(),
        "active_attendants": AutoAttendant.query.filter_by(is_active=True).count(),
    }
    return render_template("overview.html", stats=stats)


@calls_bp.route("/queues", methods=["GET"])
@login_required
def list_queues():
    """List all call queues."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    search = request.args.get("q", "").strip()

    q = CallQueue.query
    if search:
        q = q.filter(CallQueue.display_name.ilike(f"%{search}%"))

    q = q.order_by(CallQueue.display_name.asc())
    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    queues = q.offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "queues.html",
        queues=queues,
        search=search,
        page=page,
        pages=pages,
        total=total,
    )


@calls_bp.route("/auto-attendants", methods=["GET"])
@login_required
def list_auto_attendants():
    """List all auto attendants."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    search = request.args.get("q", "").strip()

    q = AutoAttendant.query
    if search:
        q = q.filter(AutoAttendant.display_name.ilike(f"%{search}%"))

    q = q.order_by(AutoAttendant.display_name.asc())
    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    attendants = q.offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "auto_attendants.html",
        attendants=attendants,
        search=search,
        page=page,
        pages=pages,
        total=total,
    )


@calls_bp.route("/sync", methods=["POST"])
@login_required
@gui_admin_required
def sync_calls():
    """Sync call queues and auto attendants from Graph API."""
    try:
        from app.services.graph_client import graph_client
        from datetime import datetime, timezone

        # Sync call queues
        try:
            graph_queues = graph_client.list_call_queues()
            queue_count = 0
            for gq in graph_queues:
                cq = CallQueue.query.filter_by(ms_queue_id=gq["id"]).first()
                if cq is None:
                    cq = CallQueue(ms_queue_id=gq["id"])
                    db.session.add(cq)
                cq.display_name    = gq.get("displayName", "")
                cq.agent_count     = len(gq.get("agents", []))
                cq.last_synced_at  = datetime.now(timezone.utc)
                queue_count += 1
        except Exception as exc:
            logger.warning(f"[Calls] Call queue sync unavailable: {exc}")
            queue_count = 0

        # Sync auto attendants
        try:
            graph_attendants = graph_client.list_auto_attendants()
            attendant_count = 0
            for ga in graph_attendants:
                aa = AutoAttendant.query.filter_by(ms_attendant_id=ga["id"]).first()
                if aa is None:
                    aa = AutoAttendant(ms_attendant_id=ga["id"])
                    db.session.add(aa)
                aa.display_name    = ga.get("displayName", "")
                aa.language        = ga.get("languageId", "en-US")
                aa.last_synced_at  = datetime.now(timezone.utc)
                attendant_count += 1
        except Exception as exc:
            logger.warning(f"[Calls] Auto attendant sync unavailable: {exc}")
            attendant_count = 0

        db.session.commit()

        AuditLog.write(
            action="SYNC",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="calls",
            payload_after={
                "queues_synced": queue_count,
                "attendants_synced": attendant_count,
            },
            status="success",
        )
        flash(
            f"Synced {queue_count} call queues and "
            f"{attendant_count} auto attendants.",
            "success",
        )
    except Exception as exc:
        logger.error(f"[Calls] Sync failed: {exc}")
        flash(f"Sync failed: {exc}", "danger")

    return redirect(url_for("calls.overview"))
