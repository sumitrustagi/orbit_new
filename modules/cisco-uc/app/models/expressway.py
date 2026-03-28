"""Expressway / VCS models — Expressway nodes and Zones."""
from app.extensions import db
from app.models.mixins import TimestampMixin


class Expressway(TimestampMixin, db.Model):
    __tablename__ = "expressways"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(128), unique=True, nullable=False, index=True)
    host            = db.Column(db.String(200), nullable=False)
    node_type       = db.Column(db.String(20), nullable=False)  # Core, Edge
    serial_number   = db.Column(db.String(60), nullable=True)
    software_version = db.Column(db.String(40), nullable=True)
    status          = db.Column(db.String(30), default="Unknown")  # Active, Inactive, Unknown
    uptime          = db.Column(db.String(60), nullable=True)
    system_name     = db.Column(db.String(128), nullable=True)
    hardware_version = db.Column(db.String(60), nullable=True)
    active_calls    = db.Column(db.Integer, default=0)
    max_calls       = db.Column(db.Integer, nullable=True)
    active_registrations = db.Column(db.Integer, default=0)
    max_registrations    = db.Column(db.Integer, nullable=True)
    mra_enabled     = db.Column(db.Boolean, default=False)
    b2b_enabled     = db.Column(db.Boolean, default=False)
    cluster_name    = db.Column(db.String(128), nullable=True)
    last_polled     = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Expressway {self.name!r} ({self.node_type})>"


class Zone(TimestampMixin, db.Model):
    __tablename__ = "zones"

    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(128), nullable=False, index=True)
    zone_type        = db.Column(db.String(60), nullable=True)  # Neighbor, Traversal Client, Traversal Server, CUCM, DNS
    peer_address     = db.Column(db.String(200), nullable=True)
    peer_port        = db.Column(db.Integer, nullable=True)
    transport        = db.Column(db.String(10), nullable=True)  # TCP, TLS
    status           = db.Column(db.String(30), default="Unknown")  # Active, Inactive
    direction        = db.Column(db.String(20), nullable=True)  # Inbound, Outbound, Both
    sip_mode         = db.Column(db.String(20), nullable=True)  # On, Off
    h323_mode        = db.Column(db.String(20), nullable=True)  # On, Off
    search_rules     = db.Column(db.Text, nullable=True)
    expressway_id    = db.Column(db.Integer, db.ForeignKey("expressways.id"), nullable=True)
    expressway       = db.relationship("Expressway", backref=db.backref("zones", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<Zone {self.name!r} ({self.zone_type})>"
