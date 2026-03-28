"""
Authentication Blueprint.

Routes:
  GET/POST /admin/login       → Login page
  GET      /admin/logout      → Logout
"""
import logging

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash,
)
from flask_login import login_required, logout_user, current_user, login_user

from app.models.user import User
from app.models.audit import AuditLog
from app.forms.auth_forms import LoginForm
from app.utils.decorators import _get_ip

logger = logging.getLogger(__name__)

auth_bp = Blueprint(
    "auth", __name__,
    template_folder="../templates/auth",
    url_prefix="/admin",
)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Display the login form and handle local authentication."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.username == form.username.data) |
            (User.email == form.username.data)
        ).first()

        if user is None or not user.check_password(form.password.data):
            if user:
                user.increment_failed_login()
                from app.extensions import db
                db.session.commit()
            AuditLog.write(
                action="LOGIN_FAILED",
                username=form.username.data,
                ip_address=_get_ip(),
                status="failure",
            )
            flash("Invalid username or password.", "danger")
            return render_template("login.html", form=form)

        if not user.is_active:
            flash("Your account has been deactivated.", "danger")
            return render_template("login.html", form=form)

        if user.is_locked:
            flash("Account temporarily locked. Try again later.", "warning")
            return render_template("login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        user.update_last_login(_get_ip())
        from app.extensions import db
        db.session.commit()

        AuditLog.write(
            action="LOGIN",
            user_id=user.id,
            username=user.username,
            user_role=user.role.value,
            ip_address=_get_ip(),
            status="success",
        )
        logger.info(f"[Auth] User '{user.username}' logged in from {_get_ip()}")

        next_page = request.args.get("next", url_for("dashboard.index"))
        return redirect(next_page)

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user."""
    username = current_user.username
    AuditLog.write(
        action="LOGOUT",
        user_id=current_user.id,
        username=username,
        user_role=current_user.role.value,
        ip_address=_get_ip(),
    )
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
