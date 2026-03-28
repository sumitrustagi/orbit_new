"""Expressway routes — nodes, zones, status."""
from flask import Blueprint, render_template, request
from flask_login import login_required

from app.extensions import db
from app.models.expressway import Expressway, Zone

expressway_bp = Blueprint("expressway", __name__, url_prefix="/expressway", template_folder="../templates/expressway")


@expressway_bp.route("/nodes")
@login_required
def nodes():
    page = request.args.get("page", 1, type=int)
    items = Expressway.query.order_by(Expressway.name).paginate(page=page, per_page=25, error_out=False)
    return render_template("nodes.html", nodes=items)


@expressway_bp.route("/nodes/<int:node_id>")
@login_required
def node_detail(node_id):
    node = Expressway.query.get_or_404(node_id)
    zones = Zone.query.filter_by(expressway_id=node.id).order_by(Zone.name).all()
    return render_template("node_detail.html", node=node, zones=zones)


@expressway_bp.route("/zones")
@login_required
def zones():
    page = request.args.get("page", 1, type=int)
    items = Zone.query.order_by(Zone.name).paginate(page=page, per_page=25, error_out=False)
    return render_template("zones.html", zones=items)


@expressway_bp.route("/zones/<int:zone_id>")
@login_required
def zone_detail(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    return render_template("zone_detail.html", zone=zone)
