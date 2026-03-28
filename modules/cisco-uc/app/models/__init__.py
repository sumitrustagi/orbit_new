"""Import all models so Alembic can detect them."""
from app.models.user import User                        # noqa: F401
from app.models.audit import AuditLog                   # noqa: F401
from app.models.app_config import AppConfig             # noqa: F401
from app.models.cucm import (                           # noqa: F401
    Phone, DevicePool, Partition, CallingSearchSpace,
    RoutePattern, TranslationPattern, Gateway, Trunk,
)
from app.models.unity import UnityMailbox, UnityUser    # noqa: F401
from app.models.imp import IMPUser                      # noqa: F401
from app.models.expressway import Expressway, Zone      # noqa: F401
