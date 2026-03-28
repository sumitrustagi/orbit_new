"""System-level tasks — health ping, audit purge."""
import logging
from datetime import datetime, timezone, timedelta

from app.extensions import celery, db
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.system_tasks.health_ping")
def health_ping():
    try:
        audit = AuditLog(
            username="system", action="HEALTH_PING",
            category="system", detail="Celery health check OK",
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Health ping failed: {e}")


@celery.task(name="app.tasks.system_tasks.purge_old_audit_logs")
def purge_old_audit_logs(days: int = 90):
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted = AuditLog.query.filter(AuditLog.timestamp < cutoff).delete()
        db.session.commit()
        logger.info(f"Purged {deleted} audit logs older than {days} days")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Audit log purge failed: {e}")
