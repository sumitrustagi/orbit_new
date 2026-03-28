"""
Task Monitor Blueprint.

Routes:
  GET  /admin/tasks/                  → Live task monitor dashboard
  GET  /admin/tasks/history           → Paginated task execution history
  POST /admin/tasks/trigger/<name>    → Manually trigger a named task
  GET  /admin/tasks/api/status        → AJAX: live worker + queue stats
  GET  /admin/tasks/api/recent        → AJAX: recent task executions
"""
import logging
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request,
    jsonify, redirect, url_for, flash,
)
from flask_login import login_required, current_user

from app.utils.decorators import superadmin_required
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

tasks_bp = Blueprint(
    "tasks", __name__,
    template_folder="../templates/tasks",
    url_prefix="/admin/tasks",
)

TRIGGERABLE_TASKS = {
    "sync_teams": {
        "task":  "app.tasks.teams_sync.sync_all_teams",
        "label": "Sync All Teams",
        "queue": "graph_sync",
    },
    "sync_users": {
        "task":  "app.tasks.teams_sync.sync_graph_users",
        "label": "Sync Graph Users",
        "queue": "graph_sync",
    },
    "sync_calls": {
        "task":  "app.tasks.teams_sync.sync_call_resources",
        "label": "Sync Call Queues & Auto Attendants",
        "queue": "graph_sync",
    },
    "purge_audit": {
        "task":  "app.tasks.maintenance.purge_old_audit_logs",
        "label": "Purge Old Audit Logs",
        "queue": "maintenance",
    },
    "health_ping": {
        "task":  "app.tasks.maintenance.health_ping",
        "label": "Health Ping",
        "queue": "maintenance",
    },
}


@tasks_bp.route("/", methods=["GET"])
@login_required
@superadmin_required
def monitor():
    """Live task monitor dashboard."""
    return render_template(
        "monitor.html",
        triggerable=TRIGGERABLE_TASKS,
    )


@tasks_bp.route("/history", methods=["GET"])
@login_required
@superadmin_required
def history():
    """Paginated task execution history from AuditLog."""
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 50
    action   = request.args.get("action", "").strip()

    TASK_ACTIONS = [
        "SYNC", "TASK_TRIGGER", "HEALTH_PING",
    ]
    q = AuditLog.query.filter(AuditLog.username == "celery")
    if action:
        q = q.filter(AuditLog.action == action)

    q      = q.order_by(AuditLog.created_at.desc())
    total  = q.count()
    pages  = max(1, (total + per_page - 1) // per_page)
    items  = q.offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "history.html",
        items=items,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        action=action,
        task_actions=TASK_ACTIONS,
    )


@tasks_bp.route("/trigger/<name>", methods=["POST"])
@login_required
@superadmin_required
def trigger_task(name: str):
    """Manually enqueue one of the allowlisted tasks."""
    task_def = TRIGGERABLE_TASKS.get(name)
    if not task_def:
        if request.is_json:
            return jsonify({"success": False, "message": "Unknown task."}), 400
        flash("Unknown task.", "danger")
        return redirect(url_for("tasks.monitor"))

    try:
        from app.extensions import celery
        result = celery.send_task(
            task_def["task"],
            queue=task_def["queue"],
        )
        AuditLog.write(
            action="TASK_TRIGGER",
            username=current_user.username if current_user.is_authenticated else "unknown",
            user_role=current_user.role.value if current_user.is_authenticated else "unknown",
            resource_type="celery_task",
            resource_name=task_def["task"],
            payload_after={"task_id": result.id, "queue": task_def["queue"]},
            status="success",
        )
        msg = f"Task '{task_def['label']}' queued (ID: {result.id[:8]}...)."
        logger.info(f"[TaskMonitor] Manual trigger: {task_def['task']} -> {result.id}")

        if request.is_json:
            return jsonify({"success": True, "message": msg, "task_id": result.id})

        flash(msg, "success")

    except Exception as exc:
        logger.error(f"[TaskMonitor] Trigger failed for '{name}': {exc}")
        if request.is_json:
            return jsonify({"success": False, "message": str(exc)}), 500
        flash(f"Failed to queue task: {exc}", "danger")

    return redirect(url_for("tasks.monitor"))


@tasks_bp.route("/api/status", methods=["GET"])
@login_required
@superadmin_required
def api_status():
    """Return live Celery worker and queue statistics."""
    try:
        from app.extensions import celery
        inspector = celery.control.inspect(timeout=3)

        active_tasks = inspector.active()  or {}
        reserved     = inspector.reserved() or {}
        stats        = inspector.stats()    or {}

        workers = []
        for worker_name, worker_stats in stats.items():
            workers.append({
                "name":      worker_name,
                "active":    len(active_tasks.get(worker_name, [])),
                "reserved":  len(reserved.get(worker_name, [])),
                "pool_size": (
                    worker_stats.get("pool", {}).get("max-concurrency", "—")
                ),
            })

        return jsonify({
            "ok":           True,
            "worker_count": len(workers),
            "workers":      workers,
            "ts":           datetime.now(timezone.utc).isoformat(),
        })

    except Exception as exc:
        return jsonify({
            "ok":           False,
            "worker_count": 0,
            "workers":      [],
            "error":        str(exc),
            "ts":           datetime.now(timezone.utc).isoformat(),
        })


@tasks_bp.route("/api/recent", methods=["GET"])
@login_required
@superadmin_required
def api_recent():
    """Return the 30 most recent celery task audit log entries."""
    logs = (
        AuditLog.query
        .filter(AuditLog.username == "celery")
        .order_by(AuditLog.created_at.desc())
        .limit(30)
        .all()
    )
    return jsonify([
        {
            "action":        log.action,
            "resource_type": log.resource_type or "",
            "resource_name": log.resource_name or "",
            "status":        log.status,
            "payload":       log.payload_after or {},
            "created_at":    log.created_at.strftime("%d %b %Y %H:%M:%S UTC")
                             if log.created_at else "",
        }
        for log in logs
    ])
