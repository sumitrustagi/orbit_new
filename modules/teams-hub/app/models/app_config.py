"""
AppConfig model — dynamic runtime configuration stored in the database.
"""
from datetime import datetime, timezone
from app.extensions import db


class AppConfig(db.Model):
    __tablename__ = "app_config"

    id          = db.Column(db.Integer, primary_key=True)
    key         = db.Column(db.String(128), unique=True, nullable=False, index=True)
    value       = db.Column(db.Text, nullable=True)
    is_encrypted = db.Column(db.Boolean, default=False, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at  = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """Return the plaintext value for key, decrypting if necessary."""
        row = cls.query.filter_by(key=key).first()
        if row is None:
            return default
        if row.is_encrypted and row.value:
            from app.utils.crypto import decrypt
            return decrypt(row.value)
        return row.value or default

    @classmethod
    def get_all(cls) -> dict:
        """Return all config values as a dict."""
        rows = cls.query.order_by(cls.key.asc()).all()
        return {
            r.key: ("***" if r.is_encrypted else (r.value or ""))
            for r in rows
        }

    @classmethod
    def set(
        cls,
        key:         str,
        value:       str,
        encrypted:   bool = False,
        description: str  = "",
    ) -> "AppConfig":
        """Upsert a config key. Commits immediately."""
        row = cls.query.filter_by(key=key).first()
        if row is None:
            row = cls(key=key)
            db.session.add(row)

        row.value        = value
        row.is_encrypted = encrypted
        row.updated_at   = datetime.now(timezone.utc)
        if description:
            row.description = description

        db.session.commit()
        return row

    @classmethod
    def delete(cls, key: str) -> bool:
        """Delete a config key. Returns True if it existed."""
        row = cls.query.filter_by(key=key).first()
        if row:
            db.session.delete(row)
            db.session.commit()
            return True
        return False

    def __repr__(self):
        return f"<AppConfig {self.key}={'[enc]' if self.is_encrypted else self.value}>"
