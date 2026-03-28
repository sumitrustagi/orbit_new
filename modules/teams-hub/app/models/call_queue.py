"""
Call Queue and Auto Attendant models — cached representations of
Microsoft Teams voice resources synced via the Graph API.
"""
from datetime import datetime, timezone

from app.extensions import db
from .mixins import TimestampMixin


class CallQueue(TimestampMixin, db.Model):
    __tablename__ = "call_queues"

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ms_queue_id         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name        = db.Column(db.String(255), nullable=False)
    phone_number        = db.Column(db.String(30), nullable=True)

    # Queue settings
    routing_method      = db.Column(db.String(32), nullable=True, default="round_robin")
    agent_count         = db.Column(db.Integer, nullable=False, default=0)
    timeout_seconds     = db.Column(db.Integer, nullable=True, default=120)
    overflow_action     = db.Column(db.String(64), nullable=True, default="disconnect")
    is_active           = db.Column(db.Boolean, nullable=False, default=True)

    # Music on hold
    music_on_hold       = db.Column(db.String(255), nullable=True)

    # Sync metadata
    last_synced_at      = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "ms_queue_id":      self.ms_queue_id,
            "display_name":     self.display_name,
            "phone_number":     self.phone_number or "",
            "routing_method":   self.routing_method,
            "agent_count":      self.agent_count,
            "timeout_seconds":  self.timeout_seconds,
            "overflow_action":  self.overflow_action,
            "is_active":        self.is_active,
            "last_synced_at":   self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at":       self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<CallQueue {self.display_name}>"


class AutoAttendant(TimestampMixin, db.Model):
    __tablename__ = "auto_attendants"

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ms_attendant_id     = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name        = db.Column(db.String(255), nullable=False)
    phone_number        = db.Column(db.String(30), nullable=True)

    # Settings
    language            = db.Column(db.String(20), nullable=True, default="en-US")
    time_zone           = db.Column(db.String(64), nullable=True, default="UTC")
    greeting_type       = db.Column(db.String(32), nullable=True, default="text_to_speech")
    greeting_text       = db.Column(db.Text, nullable=True)
    is_active           = db.Column(db.Boolean, nullable=False, default=True)

    # Menu options (stored as JSON)
    menu_options        = db.Column(db.JSON, nullable=True)

    # Business hours
    business_hours      = db.Column(db.JSON, nullable=True)
    after_hours_action  = db.Column(db.String(64), nullable=True, default="disconnect")

    # Sync metadata
    last_synced_at      = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "ms_attendant_id":   self.ms_attendant_id,
            "display_name":      self.display_name,
            "phone_number":      self.phone_number or "",
            "language":          self.language,
            "time_zone":         self.time_zone,
            "greeting_type":     self.greeting_type,
            "is_active":         self.is_active,
            "menu_options":      self.menu_options,
            "business_hours":    self.business_hours,
            "after_hours_action": self.after_hours_action,
            "last_synced_at":    self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at":        self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<AutoAttendant {self.display_name}>"
