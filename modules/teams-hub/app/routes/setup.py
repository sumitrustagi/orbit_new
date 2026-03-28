"""
Initial Setup Wizard Blueprint.

Routes:
  GET/POST /setup/ → First-run setup wizard (create admin account, configure Graph)
"""
import logging

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash,
)

from app.models.user import User, UserRole
from app.models.app_config import AppConfig
from app.extensions import db

logger = logging.getLogger(__name__)

setup_bp = Blueprint(
    "setup", __name__,
    template_folder="../templates/auth",
    url_prefix="/setup",
)


@setup_bp.route("/", methods=["GET", "POST"])
def initial_setup():
    """First-run setup wizard."""
    # If any user exists, setup is already done
    if User.query.first() is not None:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username   = request.form.get("username", "admin").strip()
        email      = request.form.get("email", "").strip()
        password   = request.form.get("password", "").strip()
        confirm    = request.form.get("confirm", "").strip()
        app_name   = request.form.get("app_name", "Teams Hub").strip()

        errors = []
        if not username:
            errors.append("Username is required.")
        if not email:
            errors.append("Email is required.")
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("setup.html", app_name=app_name)

        admin = User(
            username=username,
            email=email,
            first_name="Admin",
            last_name="User",
            role=UserRole.PLATFORM_ADMIN,
            is_active=True,
        )
        admin.set_password(password)
        db.session.add(admin)

        AppConfig.set("APP_NAME", app_name, description="Application display name")
        AppConfig.set("PRIMARY_COLOR", "#1E40AF", description="Primary brand color")
        AppConfig.set("ACCENT_COLOR", "#3B82F6", description="Accent brand color")

        db.session.commit()

        logger.info(f"[Setup] Initial admin account '{username}' created.")
        flash("Setup complete! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("setup.html", app_name="Teams Hub")
