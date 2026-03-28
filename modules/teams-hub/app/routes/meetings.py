"""
Meetings Blueprint.

Routes:
  GET  /admin/meetings/         → List meetings
  POST /admin/meetings/create   → Create a meeting
  POST /admin/meetings/sync     → Sync meetings from Graph
"""
import logging

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash,
)
from flask_login import login_required, current_user

from app.utils.decorators import gui_admin_required, _get_ip
from app.models.meeting import Meeting
from app.models.audit import AuditLog
from app.extensions import db
from app.forms.team_forms import CreateMeetingForm

logger = logging.getLogger(__name__)

meetings_bp = Blueprint(
    "meetings", __name__,
    template_folder="../templates/meetings",
    url_prefix="/admin/meetings",
)


@meetings_bp.route("/", methods=["GET"])
@login_required
def list_meetings():
    """List all meetings."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    search = request.args.get("q", "").strip()

    q = Meeting.query
    if search:
        q = q.filter(
            Meeting.subject.ilike(f"%{search}%") |
            Meeting.organizer_name.ilike(f"%{search}%")
        )

    q = q.order_by(Meeting.start_time.desc())
    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    meetings = q.offset((page - 1) * per_page).limit(per_page).all()

    stats = {
        "total":     Meeting.query.count(),
        "scheduled": Meeting.query.filter_by(status="scheduled").count(),
        "recurring": Meeting.query.filter_by(is_recurring=True).count(),
    }

    return render_template(
        "list.html",
        meetings=meetings,
        stats=stats,
        search=search,
        page=page,
        pages=pages,
        total=total,
    )


@meetings_bp.route("/create", methods=["GET", "POST"])
@login_required
@gui_admin_required
def create_meeting():
    """Create a new online meeting."""
    form = CreateMeetingForm()
    if form.validate_on_submit():
        try:
            from app.services.graph_client import graph_client
            result = graph_client.create_online_meeting(
                user_id=form.user_id.data,
                subject=form.subject.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
            )
            AuditLog.write(
                action="CREATE",
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role.value,
                ip_address=_get_ip(),
                resource_type="meeting",
                resource_name=form.subject.data,
                status="success",
            )
            flash(f"Meeting '{form.subject.data}' created.", "success")
            return redirect(url_for("meetings.list_meetings"))
        except Exception as exc:
            logger.error(f"[Meetings] Create failed: {exc}")
            flash(f"Failed to create meeting: {exc}", "danger")

    return render_template("create.html", form=form)
