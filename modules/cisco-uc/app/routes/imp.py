"""IM&P routes — Presence users and status."""
from flask import Blueprint, render_template, request
from flask_login import login_required

from app.extensions import db
from app.models.imp import IMPUser

imp_bp = Blueprint("imp", __name__, url_prefix="/imp", template_folder="../templates/imp")


@imp_bp.route("/users")
@login_required
def users():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    query = IMPUser.query
    if search:
        query = query.filter(
            db.or_(
                IMPUser.user_id.ilike(f"%{search}%"),
                IMPUser.display_name.ilike(f"%{search}%"),
                IMPUser.jabber_id.ilike(f"%{search}%"),
            )
        )
    items = query.order_by(IMPUser.user_id).paginate(page=page, per_page=25, error_out=False)
    return render_template("imp_users.html", users=items, search=search)


@imp_bp.route("/users/<int:user_id>")
@login_required
def user_detail(user_id):
    user = IMPUser.query.get_or_404(user_id)
    return render_template("imp_user_detail.html", user=user)
