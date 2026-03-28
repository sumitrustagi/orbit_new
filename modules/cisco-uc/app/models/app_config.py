"""Dynamic runtime configuration stored in the database."""
from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import TimestampMixin


class AppConfig(TimestampMixin, db.Model):
    __tablename__ = "app_config"

    id          = db.Column(db.Integer, primary_key=True)
    key         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    value       = db.Column(db.Text, nullable=True)
    encrypted   = db.Column(db.Boolean, default=False, nullable=False)
    category    = db.Column(db.String(40), default="general")  # general, cucm, unity, imp, expressway, mail, security
    description = db.Column(db.String(300), nullable=True)
    updated_by  = db.Column(db.String(80), nullable=True)

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        row = cls.query.filter_by(key=key).first()
        if row is None:
            return default
        if row.encrypted:
            from app.utils.crypto import decrypt_value
            return decrypt_value(row.value)
        return row.value or default

    @classmethod
    def set(cls, key: str, value: str, encrypt: bool = False,
            category: str = "general", description: str = "",
            username: str = "system") -> None:
        from app.extensions import db as _db
        row = cls.query.filter_by(key=key).first()
        if encrypt:
            from app.utils.crypto import encrypt_value
            stored = encrypt_value(value)
        else:
            stored = value
        if row:
            row.value = stored
            row.encrypted = encrypt
            row.category = category
            row.updated_by = username
            if description:
                row.description = description
        else:
            row = cls(
                key=key, value=stored, encrypted=encrypt,
                category=category, description=description,
                updated_by=username,
            )
            _db.session.add(row)
        _db.session.commit()

    def __repr__(self) -> str:
        return f"<AppConfig {self.key!r}>"
