"""User model with role-based access control."""
import enum
from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db, bcrypt
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class UserRole(enum.Enum):
    PLATFORM_ADMIN = "platform_admin"
    GUI_ADMIN      = "gui_admin"
    END_USER       = "end_user"


class User(UserMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email         = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=True)
    first_name    = db.Column(db.String(80), nullable=True)
    last_name     = db.Column(db.String(80), nullable=True)
    role          = db.Column(db.Enum(UserRole), default=UserRole.END_USER, nullable=False)
    is_active     = db.Column(db.Boolean, default=True, nullable=False)
    last_login    = db.Column(db.DateTime(timezone=True), nullable=True)
    notes         = db.Column(db.Text, nullable=True)

    # SSO fields
    auth_method   = db.Column(db.String(20), default="local")  # local, ldap, saml, oidc
    sso_subject   = db.Column(db.String(256), nullable=True)

    def set_password(self, plaintext: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(plaintext).decode("utf-8")

    def check_password(self, plaintext: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, plaintext)

    def record_login(self) -> None:
        self.last_login = datetime.now(timezone.utc)

    @property
    def display_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_platform_admin(self) -> bool:
        return self.role == UserRole.PLATFORM_ADMIN

    @property
    def is_gui_admin(self) -> bool:
        return self.role in (UserRole.PLATFORM_ADMIN, UserRole.GUI_ADMIN)

    def __repr__(self) -> str:
        return f"<User {self.username!r} role={self.role.value}>"
