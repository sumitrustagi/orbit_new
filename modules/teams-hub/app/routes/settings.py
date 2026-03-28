"""
Settings Blueprint.

Routes:
  GET/POST /admin/settings/              → General settings
  GET/POST /admin/settings/graph         → Microsoft Graph API settings
  GET/POST /admin/settings/email         → Email / SMTP settings
  GET/POST /admin/settings/security      → Security settings
  GET      /admin/settings/env           → Read-only environment variable viewer
"""
import os
import logging

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, jsonify,
)
from flask_login import login_required, current_user

from app.utils.decorators import superadmin_required, _get_ip
from app.models.app_config import AppConfig
from app.models.audit import AuditLog
from app.utils.crypto import encrypt
from app.forms.settings_forms import (
    GeneralSettingsForm, GraphSettingsForm,
    EmailSettingsForm, SecuritySettingsForm,
)

logger = logging.getLogger(__name__)

settings_bp = Blueprint(
    "settings", __name__,
    template_folder="../templates/settings",
    url_prefix="/admin/settings",
)


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
@superadmin_required
def general():
    """General application settings."""
    form = GeneralSettingsForm()

    if request.method == "GET":
        form.app_name.data      = AppConfig.get("APP_NAME", "Teams Hub")
        form.primary_color.data = AppConfig.get("PRIMARY_COLOR", "#1E40AF")
        form.accent_color.data  = AppConfig.get("ACCENT_COLOR", "#3B82F6")

    if form.validate_on_submit():
        AppConfig.set("APP_NAME",      form.app_name.data)
        AppConfig.set("PRIMARY_COLOR", form.primary_color.data)
        AppConfig.set("ACCENT_COLOR",  form.accent_color.data)

        AuditLog.write(
            action="UPDATE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="settings",
            resource_name="general",
            status="success",
        )
        flash("General settings saved.", "success")
        return redirect(url_for("settings.general"))

    return render_template("general.html", form=form)


@settings_bp.route("/graph", methods=["GET", "POST"])
@login_required
@superadmin_required
def graph():
    """Microsoft Graph API settings."""
    form = GraphSettingsForm()

    if request.method == "GET":
        form.tenant_id.data     = AppConfig.get("MS_TENANT_ID", "")
        form.client_id.data     = AppConfig.get("MS_CLIENT_ID", "")
        form.client_secret.data = ""  # Never prefill secrets

    if form.validate_on_submit():
        AppConfig.set("MS_TENANT_ID", form.tenant_id.data)
        AppConfig.set("MS_CLIENT_ID", form.client_id.data)
        if form.client_secret.data:
            AppConfig.set("MS_CLIENT_SECRET", encrypt(form.client_secret.data), encrypted=True)

        AuditLog.write(
            action="UPDATE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="settings",
            resource_name="graph_api",
            status="success",
        )
        flash("Graph API settings saved.", "success")
        return redirect(url_for("settings.graph"))

    return render_template("graph.html", form=form)


@settings_bp.route("/email", methods=["GET", "POST"])
@login_required
@superadmin_required
def email():
    """Email / SMTP settings."""
    form = EmailSettingsForm()

    if request.method == "GET":
        form.smtp_host.data     = AppConfig.get("SMTP_HOST", "")
        form.smtp_port.data     = AppConfig.get("SMTP_PORT", "587")
        form.smtp_username.data = AppConfig.get("SMTP_USERNAME", "")
        form.smtp_sender.data   = AppConfig.get("SMTP_SENDER_EMAIL", "")
        form.smtp_use_tls.data  = AppConfig.get("SMTP_USE_TLS", "true") == "true"

    if form.validate_on_submit():
        AppConfig.set("SMTP_HOST",         form.smtp_host.data or "")
        AppConfig.set("SMTP_PORT",         form.smtp_port.data or "587")
        AppConfig.set("SMTP_USERNAME",     form.smtp_username.data or "")
        AppConfig.set("SMTP_SENDER_EMAIL", form.smtp_sender.data or "")
        AppConfig.set("SMTP_USE_TLS",      "true" if form.smtp_use_tls.data else "false")
        if form.smtp_password.data:
            AppConfig.set("SMTP_PASSWORD", encrypt(form.smtp_password.data), encrypted=True)

        AuditLog.write(
            action="UPDATE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="settings",
            resource_name="email",
            status="success",
        )
        flash("Email settings saved.", "success")
        return redirect(url_for("settings.email"))

    return render_template("email.html", form=form)


@settings_bp.route("/security", methods=["GET", "POST"])
@login_required
@superadmin_required
def security():
    """Security settings."""
    form = SecuritySettingsForm()

    if request.method == "GET":
        form.session_timeout.data    = AppConfig.get("SESSION_TIMEOUT", "30")
        form.max_login_attempts.data = AppConfig.get("MAX_LOGIN_ATTEMPTS", "5")
        form.lockout_duration.data   = AppConfig.get("LOCKOUT_DURATION", "15")

    if form.validate_on_submit():
        AppConfig.set("SESSION_TIMEOUT",    form.session_timeout.data or "30")
        AppConfig.set("MAX_LOGIN_ATTEMPTS", form.max_login_attempts.data or "5")
        AppConfig.set("LOCKOUT_DURATION",   form.lockout_duration.data or "15")

        AuditLog.write(
            action="UPDATE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="settings",
            resource_name="security",
            status="success",
        )
        flash("Security settings saved.", "success")
        return redirect(url_for("settings.security"))

    return render_template("security.html", form=form)


@settings_bp.route("/env", methods=["GET"])
@login_required
@superadmin_required
def env_viewer():
    """Read-only environment variable viewer (masks secrets)."""
    SAFE_PREFIXES = (
        "FLASK_", "TEAMS_HUB_", "LOG_", "CACHE_", "RATELIMIT_",
    )
    MASKED_KEYS = (
        "SECRET_KEY", "DATABASE_URL", "MS_CLIENT_SECRET",
        "SMTP_PASSWORD", "ENCRYPTION_KEY", "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND", "REDIS_URL",
    )

    env_vars = {}
    for key in sorted(os.environ.keys()):
        if any(key.startswith(p) for p in SAFE_PREFIXES):
            env_vars[key] = os.environ[key]
        elif key in MASKED_KEYS:
            env_vars[key] = "***"
        else:
            env_vars[key] = os.environ[key]

    return render_template("env.html", env_vars=env_vars)
