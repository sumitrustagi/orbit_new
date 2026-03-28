"""
Maintenance tasks — audit log purge, health ping, etc.
"""
import logging
from datetime import datetime, timezone, timedelta

from app.extensions import celery, db
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.maintenance.purge_old_audit_logs")
def purge_old_audit_logs(days: int = 90):
    """Delete audit log entries older than N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    count = (
        AuditLog.query
        .filter(AuditLog.timestamp < cutoff)
        .delete(synchronize_session=False)
    )
    db.session.commit()

    AuditLog.write(
        action="PURGE_AUDIT",
        username="celery",
        resource_type="audit_log",
        payload_after={"deleted_count": count, "cutoff_days": days},
        status="success",
    )
    logger.info(f"[Maintenance] Purged {count} audit logs older than {days} days.")
    return {"deleted": count}


@celery.task(name="app.tasks.maintenance.health_ping")
def health_ping():
    """Simple health ping recorded in audit log."""
    AuditLog.write(
        action="HEALTH_PING",
        username="celery",
        resource_type="system",
        status="success",
    )
    logger.debug("[Maintenance] Health ping recorded.")
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}
