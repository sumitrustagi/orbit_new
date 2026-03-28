"""Audit log with SHA-256 chained integrity hashing."""
from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import AuditHashMixin


class AuditLog(AuditHashMixin, db.Model):
    __tablename__ = "audit_logs"

    id          = db.Column(db.Integer, primary_key=True)
    timestamp   = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    username    = db.Column(db.String(80), nullable=False, index=True)
    action      = db.Column(db.String(120), nullable=False, index=True)
    category    = db.Column(db.String(40), nullable=True, index=True)  # cucm, unity, imp, expressway, auth, system
    resource    = db.Column(db.String(200), nullable=True)
    detail      = db.Column(db.Text, nullable=True)
    ip_address  = db.Column(db.String(45), nullable=True)
    user_agent  = db.Column(db.String(300), nullable=True)
    http_method = db.Column(db.String(10), nullable=True)
    endpoint    = db.Column(db.String(200), nullable=True)
    status_code = db.Column(db.Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} {self.action!r} by {self.username!r}>"
