"""
Meeting model — cached representations of Microsoft Teams meetings
synced via the Graph API.
"""
from datetime import datetime, timezone

from app.extensions import db
from .mixins import TimestampMixin


class Meeting(TimestampMixin, db.Model):
    __tablename__ = "meetings"

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ms_meeting_id   = db.Column(db.String(512), unique=True, nullable=False, index=True)
    subject         = db.Column(db.String(512), nullable=True)
    organizer_id    = db.Column(db.String(255), nullable=True, index=True)
    organizer_name  = db.Column(db.String(255), nullable=True)
    organizer_email = db.Column(db.String(255), nullable=True)

    # Schedule
    start_time      = db.Column(db.DateTime(timezone=True), nullable=True)
    end_time        = db.Column(db.DateTime(timezone=True), nullable=True)
    is_recurring    = db.Column(db.Boolean, nullable=False, default=False)

    # Meeting details
    join_url        = db.Column(db.String(1024), nullable=True)
    meeting_type    = db.Column(db.String(32), nullable=True, default="scheduled")
    participant_count = db.Column(db.Integer, nullable=False, default=0)

    # Status
    status          = db.Column(db.String(32), nullable=True, default="scheduled")

    # Sync metadata
    last_synced_at  = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "ms_meeting_id":    self.ms_meeting_id,
            "subject":          self.subject or "",
            "organizer_name":   self.organizer_name or "",
            "organizer_email":  self.organizer_email or "",
            "start_time":       self.start_time.isoformat() if self.start_time else None,
            "end_time":         self.end_time.isoformat() if self.end_time else None,
            "is_recurring":     self.is_recurring,
            "join_url":         self.join_url or "",
            "meeting_type":     self.meeting_type,
            "participant_count": self.participant_count,
            "status":           self.status,
            "last_synced_at":   self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at":       self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Meeting {self.subject}>"
