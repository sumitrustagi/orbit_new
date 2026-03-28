"""Dashboard route — main overview page."""
from flask import Blueprint, render_template
from flask_login import login_required

from app.models.cucm import Phone, DevicePool, Gateway, Trunk
from app.models.unity import UnityMailbox, UnityUser
from app.models.imp import IMPUser
from app.models.expressway import Expressway, Zone
from app.models.audit import AuditLog
from app.services.axl_client import axl_client
from app.services.unity_client import unity_client
from app.services.imp_client import imp_client
from app.services.expressway_client import expressway_client

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    stats = {
        "phones": Phone.query.filter(Phone.deleted_at.is_(None)).count(),
        "device_pools": DevicePool.query.count(),
        "gateways": Gateway.query.count(),
        "trunks": Trunk.query.count(),
        "unity_mailboxes": UnityMailbox.query.count(),
        "unity_users": UnityUser.query.count(),
        "imp_users": IMPUser.query.count(),
        "expressways": Expressway.query.count(),
        "zones": Zone.query.count(),
        "registered_phones": Phone.query.filter(Phone.status == "Registered", Phone.deleted_at.is_(None)).count(),
        "unregistered_phones": Phone.query.filter(Phone.status == "Unregistered", Phone.deleted_at.is_(None)).count(),
    }

    integrations = {
        "cucm": axl_client.is_configured(),
        "unity": unity_client.is_configured(),
        "imp": imp_client.is_configured(),
        "expressway": expressway_client.is_configured(),
    }

    recent_audit = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()

    return render_template("index.html", stats=stats, integrations=integrations, recent_audit=recent_audit)
