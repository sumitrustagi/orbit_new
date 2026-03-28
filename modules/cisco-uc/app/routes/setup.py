"""First-run setup wizard."""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user

from app.extensions import db
from app.models.user import User, UserRole
from app.models.app_config import AppConfig
from app.forms.auth_forms import SetupForm

setup_bp = Blueprint("setup", __name__, template_folder="../templates/auth")


@setup_bp.route("/setup", methods=["GET", "POST"])
def wizard():
    if User.query.count() > 0:
        return redirect(url_for("auth.login"))

    form = SetupForm()
    if form.validate_on_submit():
        admin = User(
            username=form.username.data,
            email=form.email.data,
            role=UserRole.PLATFORM_ADMIN,
            is_active=True,
            auth_method="local",
        )
        admin.set_password(form.password.data)
        db.session.add(admin)

        if form.app_name.data:
            AppConfig.set("app_name", form.app_name.data, category="general", username="setup")

        if form.cucm_host.data:
            AppConfig.set("cucm_host", form.cucm_host.data, category="cucm", username="setup")
        if form.cucm_user.data:
            AppConfig.set("cucm_username", form.cucm_user.data, category="cucm", username="setup")
        if form.cucm_pass.data:
            AppConfig.set("cucm_password", form.cucm_pass.data, encrypt=True, category="cucm", username="setup")

        db.session.commit()
        login_user(admin)
        flash("Setup complete! Welcome to Cisco UC Hub.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("setup.html", form=form)
