"""
User Management Blueprint.

Routes:
  GET       /admin/users/                  → List users
  GET/POST  /admin/users/create            → Create user
  GET       /admin/users/<id>              → User detail
  GET/POST  /admin/users/<id>/edit         → Edit user
  POST      /admin/users/<id>/delete       → Delete user
  POST      /admin/users/<id>/toggle       → Toggle active status
  POST      /admin/users/<id>/password     → Admin password reset
  GET/POST  /admin/users/change-password   → Self-service password change
  GET       /admin/users/api/list          → JSON user list
"""
import logging

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, jsonify,
)
from flask_login import login_required, current_user

from app.utils.decorators import gui_admin_required, superadmin_required, _get_ip
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.extensions import db
from app.forms.user_forms import (
    CreateUserForm, EditUserForm,
    ChangePasswordForm,
)

logger = logging.getLogger(__name__)

users_bp = Blueprint(
    "users", __name__,
    template_folder="../templates/users",
    url_prefix="/admin/users",
)


@users_bp.route("/", methods=["GET"])
@login_required
@gui_admin_required
def list_users():
    """Paginated user list with search and role filter."""
    page        = max(1, int(request.args.get("page", 1)))
    per_page    = 25
    search      = request.args.get("q", "").strip()
    role_filter = request.args.get("role", "").strip()

    q = User.query.filter(User.deleted_at.is_(None))

    if search:
        like = f"%{search}%"
        q = q.filter(
            User.username.ilike(like) |
            User.email.ilike(like) |
            User.first_name.ilike(like) |
            User.last_name.ilike(like)
        )
    if role_filter:
        q = q.filter(User.role == UserRole(role_filter))

    q     = q.order_by(User.username.asc())
    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    users = q.offset((page - 1) * per_page).limit(per_page).all()

    stats = {
        "total":           User.query.filter(User.deleted_at.is_(None)).count(),
        "active":          User.query.filter_by(is_active=True, deleted_at=None).count(),
        "platform_admins": User.query.filter_by(role=UserRole.PLATFORM_ADMIN, deleted_at=None).count(),
        "gui_admins":      User.query.filter_by(role=UserRole.GUI_ADMIN, deleted_at=None).count(),
        "end_users":       User.query.filter_by(role=UserRole.END_USER, deleted_at=None).count(),
    }

    return render_template(
        "list.html",
        users=users,
        stats=stats,
        search=search,
        role_filter=role_filter,
        page=page,
        pages=pages,
        total=total,
    )


@users_bp.route("/create", methods=["GET", "POST"])
@login_required
@gui_admin_required
def create_user():
    """Create a new local user."""
    form = CreateUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already exists.", "danger")
            return render_template("form.html", form=form, action="create")
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.", "danger")
            return render_template("form.html", form=form, action="create")

        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=UserRole(form.role.data),
            is_active=form.is_active.data,
            notes=form.notes.data or "",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        AuditLog.write(
            action="CREATE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.username,
            status="success",
        )
        flash(f"User '{user.username}' created.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("form.html", form=form, action="create")


@users_bp.route("/<int:user_id>", methods=["GET"])
@login_required
@gui_admin_required
def user_detail(user_id: int):
    """User detail page."""
    user = User.query.get_or_404(user_id)
    recent_audit = (
        AuditLog.query
        .filter_by(user_id=user.id)
        .order_by(AuditLog.timestamp.desc())
        .limit(20)
        .all()
    )
    return render_template("detail.html", user=user, recent_audit=recent_audit)


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@gui_admin_required
def edit_user(user_id: int):
    """Edit an existing user."""
    user = User.query.get_or_404(user_id)
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        before = user.to_dict()
        user.email      = form.email.data
        user.first_name = form.first_name.data
        user.last_name  = form.last_name.data
        user.role       = UserRole(form.role.data)
        user.is_active  = form.is_active.data
        user.notes      = form.notes.data or ""
        db.session.commit()

        AuditLog.write(
            action="UPDATE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.username,
            payload_before=before,
            payload_after=user.to_dict(),
            status="success",
        )
        flash(f"User '{user.username}' updated.", "success")
        return redirect(url_for("users.user_detail", user_id=user.id))

    return render_template("form.html", form=form, action="edit", user=user)


@users_bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
@gui_admin_required
def delete_user(user_id: int):
    """Soft-delete a user."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete yourself.", "danger")
        return redirect(url_for("users.user_detail", user_id=user_id))

    user.soft_delete()
    user.is_active = False
    db.session.commit()

    AuditLog.write(
        action="DELETE",
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role.value,
        ip_address=_get_ip(),
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.username,
        status="success",
    )
    flash(f"User '{user.username}' deleted.", "success")
    return redirect(url_for("users.list_users"))


@users_bp.route("/<int:user_id>/toggle", methods=["POST"])
@login_required
@gui_admin_required
def toggle_user(user_id: int):
    """Toggle user active/inactive."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate yourself.", "danger")
        return redirect(url_for("users.user_detail", user_id=user_id))

    user.is_active = not user.is_active
    db.session.commit()

    status = "activated" if user.is_active else "deactivated"
    AuditLog.write(
        action="UPDATE",
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role.value,
        ip_address=_get_ip(),
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.username,
        payload_after={"is_active": user.is_active},
        status="success",
    )
    flash(f"User '{user.username}' {status}.", "success")
    return redirect(url_for("users.user_detail", user_id=user_id))


@users_bp.route("/<int:user_id>/password", methods=["POST"])
@login_required
@gui_admin_required
def change_password(user_id: int):
    """Admin-initiated password reset."""
    user = User.query.get_or_404(user_id)
    new_pw = request.form.get("new_password", "").strip()
    if not new_pw or len(new_pw) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect(url_for("users.user_detail", user_id=user_id))

    user.set_password(new_pw)
    user.must_change_password = True
    db.session.commit()

    AuditLog.write(
        action="PASSWORD_RESET",
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role.value,
        ip_address=_get_ip(),
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.username,
        status="success",
    )
    flash(f"Password reset for '{user.username}'.", "success")
    return redirect(url_for("users.user_detail", user_id=user_id))


@users_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def self_change_password():
    """Self-service password change."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return render_template("change_password.html", form=form)

        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False
        db.session.commit()

        AuditLog.write(
            action="PASSWORD_CHANGE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="user",
            resource_id=str(current_user.id),
            resource_name=current_user.username,
            status="success",
        )
        flash("Password changed successfully.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("change_password.html", form=form)


@users_bp.route("/api/list", methods=["GET"])
@login_required
@gui_admin_required
def api_list():
    """JSON endpoint for user list (used by AJAX)."""
    users = (
        User.query
        .filter(User.deleted_at.is_(None))
        .order_by(User.username.asc())
        .all()
    )
    return jsonify([u.to_dict() for u in users])
