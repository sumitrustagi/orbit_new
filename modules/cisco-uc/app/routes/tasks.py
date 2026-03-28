"""Task monitor routes — Celery status, manual triggers, history."""
from flask import Blueprint, render_template, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app.extensions import db, celery
from app.models.audit import AuditLog
from app.utils.decorators import platform_admin_required, _get_ip

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks", template_folder="../templates/tasks")


@tasks_bp.route("/")
@login_required
@platform_admin_required
def monitor():
    inspector = celery.control.inspect()
    try:
        active = inspector.active() or {}
        scheduled = inspector.scheduled() or {}
        reserved = inspector.reserved() or {}
        stats = inspector.stats() or {}
    except Exception:
        active, scheduled, reserved, stats = {}, {}, {}, {}

    return render_template("monitor.html", active=active, scheduled=scheduled, reserved=reserved, stats=stats)


@tasks_bp.route("/trigger/<task_name>", methods=["POST"])
@platform_admin_required
def trigger(task_name):
    allowed = {
        "sync_phones": "app.tasks.cucm_tasks.sync_phones",
        "sync_device_pools": "app.tasks.cucm_tasks.sync_device_pools",
        "sync_partitions": "app.tasks.cucm_tasks.sync_partitions",
        "sync_css": "app.tasks.cucm_tasks.sync_css",
        "sync_route_patterns": "app.tasks.cucm_tasks.sync_route_patterns",
        "sync_gateways": "app.tasks.cucm_tasks.sync_gateways",
        "sync_trunks": "app.tasks.cucm_tasks.sync_trunks",
        "sync_unity_users": "app.tasks.unity_tasks.sync_unity_users",
        "sync_unity_mailboxes": "app.tasks.unity_tasks.sync_unity_mailboxes",
        "sync_imp_users": "app.tasks.imp_tasks.sync_imp_users",
        "sync_expressways": "app.tasks.expressway_tasks.sync_expressways",
        "health_ping": "app.tasks.system_tasks.health_ping",
    }

    if task_name not in allowed:
        flash(f"Unknown task: {task_name}", "danger")
        return redirect(url_for("tasks.monitor"))

    try:
        celery.send_task(allowed[task_name])
        audit = AuditLog(
            username=current_user.username, action="TRIGGER_TASK",
            category="system", detail=f"Manually triggered {task_name}",
            ip_address=_get_ip(),
        )
        db.session.add(audit)
        db.session.commit()
        flash(f"Task {task_name} triggered.", "success")
    except Exception as e:
        flash(f"Failed to trigger task: {e}", "danger")

    return redirect(url_for("tasks.monitor"))


@tasks_bp.route("/history")
@login_required
@platform_admin_required
def history():
    logs = AuditLog.query.filter(
        AuditLog.action.in_(["TRIGGER_TASK", "SYNC_COMPLETE", "HEALTH_PING"])
    ).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template("history.html", logs=logs)
