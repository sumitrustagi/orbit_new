"""Unity Connection models — Mailboxes and Users."""
from app.extensions import db
from app.models.mixins import TimestampMixin


class UnityMailbox(TimestampMixin, db.Model):
    __tablename__ = "unity_mailboxes"

    id              = db.Column(db.Integer, primary_key=True)
    alias           = db.Column(db.String(128), unique=True, nullable=False, index=True)
    display_name    = db.Column(db.String(200), nullable=True)
    extension       = db.Column(db.String(30), nullable=True)
    dtmf_access_id  = db.Column(db.String(30), nullable=True)
    mailbox_type    = db.Column(db.String(40), default="User")  # User, System, Shared
    is_vm_enabled   = db.Column(db.Boolean, default=True)
    greeting_type   = db.Column(db.String(40), nullable=True)  # Standard, Alternate, Off-Hours
    max_msg_length  = db.Column(db.Integer, default=300)
    cos_name        = db.Column(db.String(128), nullable=True)  # Class of Service
    partition_name  = db.Column(db.String(128), nullable=True)
    unity_object_id = db.Column(db.String(40), unique=True, nullable=True)
    smtp_address    = db.Column(db.String(254), nullable=True)
    is_mwi_enabled  = db.Column(db.Boolean, default=True)
    send_message_on_login = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f"<UnityMailbox {self.alias!r} ext={self.extension}>"


class UnityUser(TimestampMixin, db.Model):
    __tablename__ = "unity_users"

    id              = db.Column(db.Integer, primary_key=True)
    alias           = db.Column(db.String(128), unique=True, nullable=False, index=True)
    display_name    = db.Column(db.String(200), nullable=True)
    first_name      = db.Column(db.String(80), nullable=True)
    last_name       = db.Column(db.String(80), nullable=True)
    extension       = db.Column(db.String(30), nullable=True)
    smtp_address    = db.Column(db.String(254), nullable=True)
    is_vm_enrolled  = db.Column(db.Boolean, default=False)
    cos_name        = db.Column(db.String(128), nullable=True)
    unity_object_id = db.Column(db.String(40), unique=True, nullable=True)
    is_locked       = db.Column(db.Boolean, default=False)
    ldap_type       = db.Column(db.String(40), nullable=True)  # AD, None

    def __repr__(self) -> str:
        return f"<UnityUser {self.alias!r}>"
