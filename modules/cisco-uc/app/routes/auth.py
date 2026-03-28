"""Authentication routes — login, logout."""
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user

from app.extensions import db, limiter
from app.models.user import User
from app.models.audit import AuditLog
from app.forms.auth_forms import LoginForm
from app.utils.decorators import _get_ip

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and not user.is_deleted and user.is_active and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            user.record_login()
            db.session.commit()

            audit = AuditLog(
                username=user.username, action="LOGIN",
                category="auth", detail="Successful login",
                ip_address=_get_ip(), user_agent=request.headers.get("User-Agent", "")[:300],
                http_method="POST", endpoint="/login",
            )
            db.session.add(audit)
            db.session.commit()

            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"), code=303)

        flash("Invalid username or password.", "danger")
        audit = AuditLog(
            username=form.username.data, action="LOGIN_FAILED",
            category="auth", detail="Invalid credentials",
            ip_address=_get_ip(), user_agent=request.headers.get("User-Agent", "")[:300],
            http_method="POST", endpoint="/login",
        )
        db.session.add(audit)
        db.session.commit()

    sso_protocol = None
    return render_template("login.html", form=form, sso_protocol=sso_protocol)


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        audit = AuditLog(
            username=current_user.username, action="LOGOUT",
            category="auth", detail="User logged out",
            ip_address=_get_ip(),
        )
        db.session.add(audit)
        db.session.commit()
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
