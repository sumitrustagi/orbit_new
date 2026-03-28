"""
Dashboard Blueprint.

Routes:
  GET /admin/ → Main dashboard with summary statistics
"""
import logging

from flask import Blueprint, render_template
from flask_login import login_required

from app.models.user import User
from app.models.team import Team, Channel
from app.models.meeting import Meeting
from app.models.call_queue import CallQueue, AutoAttendant

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint(
    "dashboard", __name__,
    template_folder="../templates/dashboard",
    url_prefix="/admin",
)


@dashboard_bp.route("/", methods=["GET"])
@dashboard_bp.route("/dashboard", methods=["GET"])
@login_required
def index():
    """Render the main dashboard with summary stats."""
    stats = {
        "total_users":          User.query.filter_by(deleted_at=None).count(),
        "active_users":         User.query.filter_by(is_active=True, deleted_at=None).count(),
        "total_teams":          Team.query.count(),
        "archived_teams":       Team.query.filter_by(is_archived=True).count(),
        "total_channels":       Channel.query.count(),
        "total_meetings":       Meeting.query.count(),
        "total_call_queues":    CallQueue.query.count(),
        "total_auto_attendants": AutoAttendant.query.count(),
    }

    recent_teams = (
        Team.query
        .order_by(Team.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "index.html",
        stats=stats,
        recent_teams=recent_teams,
    )
