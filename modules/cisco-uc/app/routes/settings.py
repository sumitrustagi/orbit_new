"""Settings routes — configure CUCM, Unity, IM&P, Expressway, email, security."""
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models.app_config import AppConfig
from app.models.audit import AuditLog
from app.forms.settings_forms import (
    CUCMSettingsForm, UnitySettingsForm, IMPSettingsForm,
    ExpresswaySettingsForm, GeneralSettingsForm, EmailSettingsForm,
    SecuritySettingsForm,
)
from app.utils.decorators import platform_admin_required, _get_ip

settings_bp = Blueprint("settings", __name__, url_prefix="/settings", template_folder="../templates/settings")


@settings_bp.route("/")
@login_required
@platform_admin_required
def index():
    return render_template("settings_index.html")


@settings_bp.route("/general", methods=["GET", "POST"])
@platform_admin_required
def general():
    form = GeneralSettingsForm()
    if form.validate_on_submit():
        AppConfig.set("app_name", form.app_name.data, category="general", username=current_user.username)
        AppConfig.set("session_timeout", str(form.session_timeout.data), category="general", username=current_user.username)
        _log_settings_change("general")
        flash("General settings saved.", "success")
        return redirect(url_for("settings.index"))
    form.app_name.data = AppConfig.get("app_name", "Cisco UC Hub")
    form.session_timeout.data = int(AppConfig.get("session_timeout", "30"))
    return render_template("general.html", form=form)


@settings_bp.route("/cucm", methods=["GET", "POST"])
@platform_admin_required
def cucm():
    form = CUCMSettingsForm()
    if form.validate_on_submit():
        AppConfig.set("cucm_host", form.cucm_host.data, category="cucm", username=current_user.username)
        AppConfig.set("cucm_username", form.cucm_username.data, category="cucm", username=current_user.username)
        if form.cucm_password.data:
            AppConfig.set("cucm_password", form.cucm_password.data, encrypt=True, category="cucm", username=current_user.username)
        AppConfig.set("cucm_version", form.cucm_version.data, category="cucm", username=current_user.username)
        AppConfig.set("cucm_verify_ssl", "true" if form.cucm_verify_ssl.data else "false", category="cucm", username=current_user.username)
        _log_settings_change("cucm")
        flash("CUCM settings saved.", "success")
        return redirect(url_for("settings.index"))
    form.cucm_host.data = AppConfig.get("cucm_host")
    form.cucm_username.data = AppConfig.get("cucm_username")
    form.cucm_version.data = AppConfig.get("cucm_version", "14.0")
    form.cucm_verify_ssl.data = AppConfig.get("cucm_verify_ssl") == "true"
    return render_template("cucm.html", form=form)


@settings_bp.route("/unity", methods=["GET", "POST"])
@platform_admin_required
def unity():
    form = UnitySettingsForm()
    if form.validate_on_submit():
        AppConfig.set("unity_host", form.unity_host.data, category="unity", username=current_user.username)
        AppConfig.set("unity_username", form.unity_username.data, category="unity", username=current_user.username)
        if form.unity_password.data:
            AppConfig.set("unity_password", form.unity_password.data, encrypt=True, category="unity", username=current_user.username)
        AppConfig.set("unity_verify_ssl", "true" if form.unity_verify_ssl.data else "false", category="unity", username=current_user.username)
        _log_settings_change("unity")
        flash("Unity Connection settings saved.", "success")
        return redirect(url_for("settings.index"))
    form.unity_host.data = AppConfig.get("unity_host")
    form.unity_username.data = AppConfig.get("unity_username")
    form.unity_verify_ssl.data = AppConfig.get("unity_verify_ssl") == "true"
    return render_template("unity.html", form=form)


@settings_bp.route("/imp", methods=["GET", "POST"])
@platform_admin_required
def imp():
    form = IMPSettingsForm()
    if form.validate_on_submit():
        AppConfig.set("imp_host", form.imp_host.data, category="imp", username=current_user.username)
        AppConfig.set("imp_username", form.imp_username.data, category="imp", username=current_user.username)
        if form.imp_password.data:
            AppConfig.set("imp_password", form.imp_password.data, encrypt=True, category="imp", username=current_user.username)
        AppConfig.set("imp_verify_ssl", "true" if form.imp_verify_ssl.data else "false", category="imp", username=current_user.username)
        _log_settings_change("imp")
        flash("IM&P settings saved.", "success")
        return redirect(url_for("settings.index"))
    form.imp_host.data = AppConfig.get("imp_host")
    form.imp_username.data = AppConfig.get("imp_username")
    form.imp_verify_ssl.data = AppConfig.get("imp_verify_ssl") == "true"
    return render_template("imp.html", form=form)


@settings_bp.route("/expressway", methods=["GET", "POST"])
@platform_admin_required
def expressway():
    form = ExpresswaySettingsForm()
    if form.validate_on_submit():
        AppConfig.set("expressway_host", form.expressway_host.data, category="expressway", username=current_user.username)
        AppConfig.set("expressway_username", form.expressway_username.data, category="expressway", username=current_user.username)
        if form.expressway_password.data:
            AppConfig.set("expressway_password", form.expressway_password.data, encrypt=True, category="expressway", username=current_user.username)
        AppConfig.set("expressway_verify_ssl", "true" if form.expressway_verify_ssl.data else "false", category="expressway", username=current_user.username)
        _log_settings_change("expressway")
        flash("Expressway settings saved.", "success")
        return redirect(url_for("settings.index"))
    form.expressway_host.data = AppConfig.get("expressway_host")
    form.expressway_username.data = AppConfig.get("expressway_username")
    form.expressway_verify_ssl.data = AppConfig.get("expressway_verify_ssl") == "true"
    return render_template("expressway.html", form=form)


@settings_bp.route("/email", methods=["GET", "POST"])
@platform_admin_required
def email():
    form = EmailSettingsForm()
    if form.validate_on_submit():
        AppConfig.set("smtp_host", form.smtp_host.data, category="mail", username=current_user.username)
        AppConfig.set("smtp_port", str(form.smtp_port.data), category="mail", username=current_user.username)
        AppConfig.set("smtp_username", form.smtp_username.data, category="mail", username=current_user.username)
        if form.smtp_password.data:
            AppConfig.set("smtp_password", form.smtp_password.data, encrypt=True, category="mail", username=current_user.username)
        AppConfig.set("smtp_use_tls", "true" if form.smtp_use_tls.data else "false", category="mail", username=current_user.username)
        AppConfig.set("smtp_sender", form.smtp_sender.data, category="mail", username=current_user.username)
        _log_settings_change("email")
        flash("Email settings saved.", "success")
        return redirect(url_for("settings.index"))
    form.smtp_host.data = AppConfig.get("smtp_host")
    form.smtp_port.data = int(AppConfig.get("smtp_port", "587"))
    form.smtp_username.data = AppConfig.get("smtp_username")
    form.smtp_use_tls.data = AppConfig.get("smtp_use_tls", "true") == "true"
    form.smtp_sender.data = AppConfig.get("smtp_sender")
    return render_template("email.html", form=form)


@settings_bp.route("/security", methods=["GET", "POST"])
@platform_admin_required
def security():
    form = SecuritySettingsForm()
    if form.validate_on_submit():
        AppConfig.set("password_min_length", str(form.password_min_length.data), category="security", username=current_user.username)
        AppConfig.set("password_require_upper", "true" if form.password_require_upper.data else "false", category="security", username=current_user.username)
        AppConfig.set("password_require_digit", "true" if form.password_require_digit.data else "false", category="security", username=current_user.username)
        AppConfig.set("password_require_special", "true" if form.password_require_special.data else "false", category="security", username=current_user.username)
        AppConfig.set("max_login_attempts", str(form.max_login_attempts.data), category="security", username=current_user.username)
        AppConfig.set("lockout_duration", str(form.lockout_duration.data), category="security", username=current_user.username)
        _log_settings_change("security")
        flash("Security settings saved.", "success")
        return redirect(url_for("settings.index"))
    form.password_min_length.data = int(AppConfig.get("password_min_length", "8"))
    form.password_require_upper.data = AppConfig.get("password_require_upper", "true") == "true"
    form.password_require_digit.data = AppConfig.get("password_require_digit", "true") == "true"
    form.password_require_special.data = AppConfig.get("password_require_special", "true") == "true"
    form.max_login_attempts.data = int(AppConfig.get("max_login_attempts", "5"))
    form.lockout_duration.data = int(AppConfig.get("lockout_duration", "15"))
    return render_template("security.html", form=form)


def _log_settings_change(category: str):
    audit = AuditLog(
        username=current_user.username,
        action="UPDATE_SETTINGS",
        category="system",
        detail=f"Updated {category} settings",
        ip_address=_get_ip(),
    )
    db.session.add(audit)
    db.session.commit()
