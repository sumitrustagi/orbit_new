"""
Team and Channel models — cached representations of Microsoft Teams
data synced via the Graph API.
"""
from datetime import datetime, timezone

from app.extensions import db
from .mixins import TimestampMixin


class Team(TimestampMixin, db.Model):
    __tablename__ = "teams"

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ms_team_id      = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name    = db.Column(db.String(255), nullable=False)
    description     = db.Column(db.Text, nullable=True)
    visibility      = db.Column(db.String(20), nullable=True, default="private")
    mail_nickname   = db.Column(db.String(255), nullable=True)
    is_archived     = db.Column(db.Boolean, nullable=False, default=False)

    # Owner / member counts (cached from Graph)
    owner_count     = db.Column(db.Integer, nullable=False, default=0)
    member_count    = db.Column(db.Integer, nullable=False, default=0)
    guest_count     = db.Column(db.Integer, nullable=False, default=0)

    # Sync metadata
    last_synced_at  = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    channels = db.relationship("Channel", back_populates="team",
                               lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "ms_team_id":    self.ms_team_id,
            "display_name":  self.display_name,
            "description":   self.description or "",
            "visibility":    self.visibility,
            "is_archived":   self.is_archived,
            "owner_count":   self.owner_count,
            "member_count":  self.member_count,
            "guest_count":   self.guest_count,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at":    self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Team {self.display_name}>"


class Channel(TimestampMixin, db.Model):
    __tablename__ = "channels"

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ms_channel_id   = db.Column(db.String(255), unique=True, nullable=False, index=True)
    team_id         = db.Column(db.Integer, db.ForeignKey("teams.id",
                                ondelete="CASCADE"), nullable=False, index=True)
    display_name    = db.Column(db.String(255), nullable=False)
    description     = db.Column(db.Text, nullable=True)
    membership_type = db.Column(db.String(20), nullable=True, default="standard")
    is_general      = db.Column(db.Boolean, nullable=False, default=False)

    # Sync metadata
    last_synced_at  = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    team = db.relationship("Team", back_populates="channels")

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "ms_channel_id":   self.ms_channel_id,
            "team_id":         self.team_id,
            "display_name":    self.display_name,
            "description":     self.description or "",
            "membership_type": self.membership_type,
            "is_general":      self.is_general,
            "last_synced_at":  self.last_synced_at.isoformat() if self.last_synced_at else None,
        }

    def __repr__(self) -> str:
        return f"<Channel {self.display_name}>"
