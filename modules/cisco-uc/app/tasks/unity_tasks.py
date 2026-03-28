"""Unity Connection background sync tasks."""
import logging

from app.extensions import celery, db
from app.models.unity import UnityMailbox, UnityUser
from app.models.audit import AuditLog
from app.services.unity_client import unity_client

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.unity_tasks.sync_unity_users")
def sync_unity_users():
    if not unity_client.is_configured():
        logger.info("Unity not configured, skipping user sync")
        return
    try:
        users = unity_client.list_users(page_size=500)
        synced = 0
        for u in users:
            alias = u.get("Alias", "")
            if not alias:
                continue
            user = UnityUser.query.filter_by(alias=alias).first()
            if user is None:
                user = UnityUser(alias=alias)
                db.session.add(user)
            user.display_name = u.get("DisplayName", "")
            user.first_name = u.get("FirstName", "")
            user.last_name = u.get("LastName", "")
            user.extension = u.get("DtmfAccessId", "")
            user.smtp_address = u.get("SmtpAddress", "")
            user.unity_object_id = u.get("ObjectId", "")
            synced += 1
        db.session.commit()
        audit = AuditLog(username="system", action="SYNC_UNITY_USERS", category="unity", detail=f"Synced {synced} Unity users")
        db.session.add(audit)
        db.session.commit()
        logger.info(f"Synced {synced} Unity users")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unity user sync failed: {e}")


@celery.task(name="app.tasks.unity_tasks.sync_unity_mailboxes")
def sync_unity_mailboxes():
    if not unity_client.is_configured():
        return
    try:
        mailboxes = unity_client.list_user_mailboxes(page_size=500)
        synced = 0
        for m in mailboxes:
            alias = m.get("Alias", "")
            if not alias:
                continue
            mb = UnityMailbox.query.filter_by(alias=alias).first()
            if mb is None:
                mb = UnityMailbox(alias=alias)
                db.session.add(mb)
            mb.display_name = m.get("DisplayName", "")
            mb.extension = m.get("DtmfAccessId", "")
            mb.smtp_address = m.get("SmtpAddress", "")
            mb.unity_object_id = m.get("ObjectId", "")
            synced += 1
        db.session.commit()
        audit = AuditLog(username="system", action="SYNC_UNITY_MAILBOXES", category="unity", detail=f"Synced {synced} Unity mailboxes")
        db.session.add(audit)
        db.session.commit()
        logger.info(f"Synced {synced} Unity mailboxes")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unity mailbox sync failed: {e}")
