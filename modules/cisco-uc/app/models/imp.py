"""IM&P (Instant Messaging & Presence) model."""
from app.extensions import db
from app.models.mixins import TimestampMixin


class IMPUser(TimestampMixin, db.Model):
    __tablename__ = "imp_users"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.String(128), unique=True, nullable=False, index=True)
    display_name    = db.Column(db.String(200), nullable=True)
    email           = db.Column(db.String(254), nullable=True)
    jabber_id       = db.Column(db.String(254), nullable=True)
    im_enabled      = db.Column(db.Boolean, default=True)
    presence_status = db.Column(db.String(40), default="Unknown")  # Available, Away, DND, Offline, Unknown
    status_message  = db.Column(db.String(300), nullable=True)
    home_cluster    = db.Column(db.String(128), nullable=True)
    device_name     = db.Column(db.String(128), nullable=True)  # Jabber device
    directory_uri   = db.Column(db.String(254), nullable=True)
    is_ucm_synced   = db.Column(db.Boolean, default=False)
    federation_enabled = db.Column(db.Boolean, default=False)
    compliance_enabled = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f"<IMPUser {self.user_id!r} status={self.presence_status}>"
