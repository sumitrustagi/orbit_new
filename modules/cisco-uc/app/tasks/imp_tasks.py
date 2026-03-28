"""IM&P background sync tasks."""
import logging

from app.extensions import celery, db
from app.models.imp import IMPUser
from app.models.audit import AuditLog
from app.services.imp_client import imp_client

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.imp_tasks.sync_imp_users")
def sync_imp_users():
    if not imp_client.is_configured():
        logger.info("IM&P not configured, skipping user sync")
        return
    try:
        users = imp_client.list_imp_users()
        synced = 0
        for u in users:
            user_id = u.get("userName", u.get("userId", ""))
            if not user_id:
                continue
            imp_user = IMPUser.query.filter_by(user_id=user_id).first()
            if imp_user is None:
                imp_user = IMPUser(user_id=user_id)
                db.session.add(imp_user)
            imp_user.display_name = u.get("displayName", "")
            imp_user.email = u.get("mailId", "")
            imp_user.jabber_id = u.get("directoryUri", u.get("jabberId", ""))
            synced += 1
        db.session.commit()
        audit = AuditLog(username="system", action="SYNC_IMP_USERS", category="imp", detail=f"Synced {synced} IM&P users")
        db.session.add(audit)
        db.session.commit()
        logger.info(f"Synced {synced} IM&P users")
    except Exception as e:
        db.session.rollback()
        logger.error(f"IM&P user sync failed: {e}")
