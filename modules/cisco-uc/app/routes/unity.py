"""Unity Connection routes — Mailboxes and Users."""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models.unity import UnityMailbox, UnityUser
from app.models.audit import AuditLog
from app.utils.decorators import gui_admin_required, _get_ip

unity_bp = Blueprint("unity", __name__, url_prefix="/unity", template_folder="../templates/unity")


@unity_bp.route("/mailboxes")
@login_required
def mailboxes():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    query = UnityMailbox.query
    if search:
        query = query.filter(
            db.or_(
                UnityMailbox.alias.ilike(f"%{search}%"),
                UnityMailbox.display_name.ilike(f"%{search}%"),
                UnityMailbox.extension.ilike(f"%{search}%"),
            )
        )
    items = query.order_by(UnityMailbox.alias).paginate(page=page, per_page=25, error_out=False)
    return render_template("mailboxes.html", mailboxes=items, search=search)


@unity_bp.route("/mailboxes/<int:mb_id>")
@login_required
def mailbox_detail(mb_id):
    mb = UnityMailbox.query.get_or_404(mb_id)
    return render_template("mailbox_detail.html", mailbox=mb)


@unity_bp.route("/users")
@login_required
def users():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    query = UnityUser.query
    if search:
        query = query.filter(
            db.or_(
                UnityUser.alias.ilike(f"%{search}%"),
                UnityUser.display_name.ilike(f"%{search}%"),
            )
        )
    items = query.order_by(UnityUser.alias).paginate(page=page, per_page=25, error_out=False)
    return render_template("unity_users.html", users=items, search=search)


@unity_bp.route("/users/<int:user_id>")
@login_required
def user_detail(user_id):
    user = UnityUser.query.get_or_404(user_id)
    return render_template("unity_user_detail.html", user=user)
