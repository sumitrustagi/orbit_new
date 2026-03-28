"""Reusable SQLAlchemy model mixins."""
import hashlib
import json
from datetime import datetime, timezone

from app.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class SoftDeleteMixin:
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.deleted_at = None


class AuditHashMixin:
    row_hash = db.Column(db.String(64), nullable=True)

    def compute_hash(self, previous_hash: str = "") -> str:
        payload = json.dumps({
            "id": self.id, "action": getattr(self, "action", ""),
            "username": getattr(self, "username", ""),
            "timestamp": str(getattr(self, "timestamp", "")),
            "prev_hash": previous_hash,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()
