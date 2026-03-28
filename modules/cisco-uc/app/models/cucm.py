"""CUCM models — Phones, Device Pools, Partitions, CSS, Route Patterns, Gateways, Trunks."""
from app.extensions import db
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Phone(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "phones"

    id                = db.Column(db.Integer, primary_key=True)
    name              = db.Column(db.String(128), unique=True, nullable=False, index=True)
    description       = db.Column(db.String(300), nullable=True)
    model             = db.Column(db.String(80), nullable=True)
    protocol          = db.Column(db.String(10), nullable=True)  # SIP, SCCP
    status            = db.Column(db.String(30), default="Unknown")  # Registered, Unregistered, Unknown
    ip_address        = db.Column(db.String(45), nullable=True)
    mac_address       = db.Column(db.String(17), nullable=True)
    firmware          = db.Column(db.String(80), nullable=True)
    directory_number  = db.Column(db.String(30), nullable=True)
    device_pool       = db.Column(db.String(128), nullable=True)
    calling_search_space = db.Column(db.String(128), nullable=True)
    location          = db.Column(db.String(128), nullable=True)
    owner_user_id     = db.Column(db.String(128), nullable=True)
    cucm_uuid         = db.Column(db.String(40), unique=True, nullable=True)
    last_seen         = db.Column(db.DateTime(timezone=True), nullable=True)
    cluster_node      = db.Column(db.String(128), nullable=True)

    def __repr__(self) -> str:
        return f"<Phone {self.name!r} ({self.model})>"


class DevicePool(TimestampMixin, db.Model):
    __tablename__ = "device_pools"

    id                    = db.Column(db.Integer, primary_key=True)
    name                  = db.Column(db.String(128), unique=True, nullable=False, index=True)
    cucm_uuid             = db.Column(db.String(40), unique=True, nullable=True)
    date_time_group       = db.Column(db.String(128), nullable=True)
    region                = db.Column(db.String(128), nullable=True)
    srst_reference        = db.Column(db.String(128), nullable=True)
    calling_search_space  = db.Column(db.String(128), nullable=True)
    media_resource_group_list = db.Column(db.String(128), nullable=True)
    description           = db.Column(db.String(300), nullable=True)

    def __repr__(self) -> str:
        return f"<DevicePool {self.name!r}>"


class Partition(TimestampMixin, db.Model):
    __tablename__ = "partitions"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(128), unique=True, nullable=False, index=True)
    cucm_uuid     = db.Column(db.String(40), unique=True, nullable=True)
    description   = db.Column(db.String(300), nullable=True)
    time_schedule = db.Column(db.String(128), nullable=True)

    def __repr__(self) -> str:
        return f"<Partition {self.name!r}>"


class CallingSearchSpace(TimestampMixin, db.Model):
    __tablename__ = "calling_search_spaces"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(128), unique=True, nullable=False, index=True)
    cucm_uuid   = db.Column(db.String(40), unique=True, nullable=True)
    description = db.Column(db.String(300), nullable=True)
    partitions  = db.Column(db.Text, nullable=True)  # stored as comma-separated

    def get_partition_list(self) -> list:
        if not self.partitions:
            return []
        return [p.strip() for p in self.partitions.split(",") if p.strip()]

    def __repr__(self) -> str:
        return f"<CallingSearchSpace {self.name!r}>"


class RoutePattern(TimestampMixin, db.Model):
    __tablename__ = "route_patterns"

    id              = db.Column(db.Integer, primary_key=True)
    pattern         = db.Column(db.String(128), nullable=False, index=True)
    cucm_uuid       = db.Column(db.String(40), unique=True, nullable=True)
    description     = db.Column(db.String(300), nullable=True)
    partition       = db.Column(db.String(128), nullable=True)
    gateway         = db.Column(db.String(128), nullable=True)
    route_list      = db.Column(db.String(128), nullable=True)
    block_enabled   = db.Column(db.Boolean, default=False)
    urgent_priority = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f"<RoutePattern {self.pattern!r}>"


class TranslationPattern(TimestampMixin, db.Model):
    __tablename__ = "translation_patterns"

    id                       = db.Column(db.Integer, primary_key=True)
    pattern                  = db.Column(db.String(128), nullable=False, index=True)
    cucm_uuid                = db.Column(db.String(40), unique=True, nullable=True)
    description              = db.Column(db.String(300), nullable=True)
    partition                = db.Column(db.String(128), nullable=True)
    calling_search_space     = db.Column(db.String(128), nullable=True)
    called_party_transform   = db.Column(db.String(128), nullable=True)
    calling_party_transform  = db.Column(db.String(128), nullable=True)
    prefix_digits            = db.Column(db.String(30), nullable=True)
    discard_digits            = db.Column(db.String(60), nullable=True)

    def __repr__(self) -> str:
        return f"<TranslationPattern {self.pattern!r}>"


class Gateway(TimestampMixin, db.Model):
    __tablename__ = "gateways"

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(128), unique=True, nullable=False, index=True)
    cucm_uuid    = db.Column(db.String(40), unique=True, nullable=True)
    description  = db.Column(db.String(300), nullable=True)
    ip_address   = db.Column(db.String(45), nullable=True)
    gateway_type = db.Column(db.String(60), nullable=True)  # MGCP, H323, SIP
    protocol     = db.Column(db.String(20), nullable=True)
    status       = db.Column(db.String(30), default="Unknown")
    vendor       = db.Column(db.String(80), nullable=True)
    model        = db.Column(db.String(80), nullable=True)
    port_count   = db.Column(db.Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Gateway {self.name!r} ({self.gateway_type})>"


class Trunk(TimestampMixin, db.Model):
    __tablename__ = "trunks"

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(128), unique=True, nullable=False, index=True)
    cucm_uuid            = db.Column(db.String(40), unique=True, nullable=True)
    description          = db.Column(db.String(300), nullable=True)
    trunk_type           = db.Column(db.String(40), nullable=True)  # SIP, H323
    device_pool          = db.Column(db.String(128), nullable=True)
    calling_search_space = db.Column(db.String(128), nullable=True)
    destination_address  = db.Column(db.String(200), nullable=True)
    destination_port     = db.Column(db.Integer, nullable=True)
    sip_profile          = db.Column(db.String(128), nullable=True)
    security_profile     = db.Column(db.String(128), nullable=True)
    status               = db.Column(db.String(30), default="Unknown")

    def __repr__(self) -> str:
        return f"<Trunk {self.name!r} ({self.trunk_type})>"
