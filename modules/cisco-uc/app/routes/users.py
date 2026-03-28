"""User management routes."""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.forms.user_forms import UserCreateForm, UserEditForm, ChangePasswordForm
from app.utils.decorators import platform_admin_required, _get_ip

users_bp = Blueprint("users", __name__, url_prefix="/users", template_folder="../templates/users")


@users_bp.route("/")
@login_required
@platform_admin_required
def list_users():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    query = User.query.filter(User.deleted_at.is_(None))
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
            )
        )
    users = query.order_by(User.username).paginate(page=page, per_page=25, error_out=False)
    return render_template("list.html", users=users, search=search)


@users_bp.route("/create", methods=["GET", "POST"])
@platform_admin_required
def create():
    form = UserCreateForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already exists.", "danger")
            return render_template("form.html", form=form, title="Create User")
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already exists.", "danger")
            return render_template("form.html", form=form, title="Create User")

        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=UserRole(form.role.data),
            is_active=form.is_active.data,
            notes=form.notes.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)

        audit = AuditLog(
            username=current_user.username, action="CREATE_USER",
            category="auth", resource=user.username,
            detail=f"Created user {user.username} with role {user.role.value}",
            ip_address=_get_ip(),
        )
        db.session.add(audit)
        db.session.commit()
        flash(f"User {user.username} created.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("form.html", form=form, title="Create User")


@users_bp.route("/<int:user_id>")
@login_required
def detail(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("detail.html", user=user)


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@platform_admin_required
def edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role = UserRole(form.role.data)
        user.is_active = form.is_active.data
        user.notes = form.notes.data

        audit = AuditLog(
            username=current_user.username, action="UPDATE_USER",
            category="auth", resource=user.username,
            detail=f"Updated user {user.username}",
            ip_address=_get_ip(),
        )
        db.session.add(audit)
        db.session.commit()
        flash(f"User {user.username} updated.", "success")
        return redirect(url_for("users.detail", user_id=user.id))

    form.role.data = user.role.value
    return render_template("form.html", form=form, title=f"Edit {user.username}", user=user)


@users_bp.route("/<int:user_id>/delete", methods=["POST"])
@platform_admin_required
def delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users.list_users"))
    user.soft_delete()
    audit = AuditLog(
        username=current_user.username, action="DELETE_USER",
        category="auth", resource=user.username,
        detail=f"Soft-deleted user {user.username}",
        ip_address=_get_ip(),
    )
    db.session.add(audit)
    db.session.commit()
    flash(f"User {user.username} deleted.", "success")
    return redirect(url_for("users.list_users"))


@users_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return render_template("change_password.html", form=form)
        current_user.set_password(form.new_password.data)
        audit = AuditLog(
            username=current_user.username, action="CHANGE_PASSWORD",
            category="auth", detail="User changed their password",
            ip_address=_get_ip(),
        )
        db.session.add(audit)
        db.session.commit()
        flash("Password changed successfully.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("change_password.html", form=form)
