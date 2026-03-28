"""CUCM routes — Phones, Device Pools, Partitions, CSS, Routes, Gateways, Trunks."""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models.cucm import (
    Phone, DevicePool, Partition, CallingSearchSpace,
    RoutePattern, TranslationPattern, Gateway, Trunk,
)
from app.models.audit import AuditLog
from app.forms.cucm_forms import PhoneSearchForm
from app.utils.decorators import gui_admin_required, _get_ip

cucm_bp = Blueprint("cucm", __name__, url_prefix="/cucm", template_folder="../templates/cucm")


# ── Phones ────────────────────────────────────────────────────────────────

@cucm_bp.route("/phones")
@login_required
def phones():
    form = PhoneSearchForm(request.args)
    page = request.args.get("page", 1, type=int)
    query = Phone.query.filter(Phone.deleted_at.is_(None))

    search_value = request.args.get("search_value", "").strip()
    search_field = request.args.get("search_field", "name")
    if search_value:
        col = getattr(Phone, search_field, Phone.name)
        query = query.filter(col.ilike(f"%{search_value}%"))

    phones = query.order_by(Phone.name).paginate(page=page, per_page=25, error_out=False)
    return render_template("phones.html", phones=phones, form=form)


@cucm_bp.route("/phones/<int:phone_id>")
@login_required
def phone_detail(phone_id):
    phone = Phone.query.get_or_404(phone_id)
    return render_template("phone_detail.html", phone=phone)


@cucm_bp.route("/phones/<int:phone_id>/delete", methods=["POST"])
@gui_admin_required
def phone_delete(phone_id):
    phone = Phone.query.get_or_404(phone_id)
    phone.soft_delete()
    audit = AuditLog(
        username=current_user.username, action="DELETE_PHONE",
        category="cucm", resource=phone.name,
        detail=f"Soft-deleted phone {phone.name}",
        ip_address=_get_ip(),
    )
    db.session.add(audit)
    db.session.commit()
    flash(f"Phone {phone.name} deleted.", "success")
    return redirect(url_for("cucm.phones"))


# ── Device Pools ──────────────────────────────────────────────────────────

@cucm_bp.route("/device-pools")
@login_required
def device_pools():
    page = request.args.get("page", 1, type=int)
    pools = DevicePool.query.order_by(DevicePool.name).paginate(page=page, per_page=25, error_out=False)
    return render_template("device_pools.html", pools=pools)


# ── Partitions ────────────────────────────────────────────────────────────

@cucm_bp.route("/partitions")
@login_required
def partitions():
    page = request.args.get("page", 1, type=int)
    parts = Partition.query.order_by(Partition.name).paginate(page=page, per_page=25, error_out=False)
    return render_template("partitions.html", partitions=parts)


# ── Calling Search Spaces ────────────────────────────────────────────────

@cucm_bp.route("/css")
@login_required
def css_list():
    page = request.args.get("page", 1, type=int)
    items = CallingSearchSpace.query.order_by(CallingSearchSpace.name).paginate(page=page, per_page=25, error_out=False)
    return render_template("css.html", css_items=items)


# ── Route Patterns ────────────────────────────────────────────────────────

@cucm_bp.route("/route-patterns")
@login_required
def route_patterns():
    page = request.args.get("page", 1, type=int)
    patterns = RoutePattern.query.order_by(RoutePattern.pattern).paginate(page=page, per_page=25, error_out=False)
    return render_template("route_patterns.html", patterns=patterns)


# ── Translation Patterns ─────────────────────────────────────────────────

@cucm_bp.route("/translation-patterns")
@login_required
def translation_patterns():
    page = request.args.get("page", 1, type=int)
    patterns = TranslationPattern.query.order_by(TranslationPattern.pattern).paginate(page=page, per_page=25, error_out=False)
    return render_template("translation_patterns.html", patterns=patterns)


# ── Gateways ──────────────────────────────────────────────────────────────

@cucm_bp.route("/gateways")
@login_required
def gateways():
    page = request.args.get("page", 1, type=int)
    items = Gateway.query.order_by(Gateway.name).paginate(page=page, per_page=25, error_out=False)
    return render_template("gateways.html", gateways=items)


@cucm_bp.route("/gateways/<int:gw_id>")
@login_required
def gateway_detail(gw_id):
    gw = Gateway.query.get_or_404(gw_id)
    return render_template("gateway_detail.html", gateway=gw)


# ── Trunks ────────────────────────────────────────────────────────────────

@cucm_bp.route("/trunks")
@login_required
def trunks():
    page = request.args.get("page", 1, type=int)
    items = Trunk.query.order_by(Trunk.name).paginate(page=page, per_page=25, error_out=False)
    return render_template("trunks.html", trunks=items)


@cucm_bp.route("/trunks/<int:trunk_id>")
@login_required
def trunk_detail(trunk_id):
    trunk = Trunk.query.get_or_404(trunk_id)
    return render_template("trunk_detail.html", trunk=trunk)
