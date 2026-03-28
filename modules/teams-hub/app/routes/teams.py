"""
Teams & Channels Blueprint.

Routes:
  GET  /admin/teams/                     → List all teams
  GET  /admin/teams/<id>                 → Team detail with channels
  POST /admin/teams/create               → Create a new team
  POST /admin/teams/<id>/archive         → Archive a team
  POST /admin/teams/<id>/unarchive       → Unarchive a team
  POST /admin/teams/<id>/delete          → Delete a team
  POST /admin/teams/<id>/channels/create → Create a channel
  POST /admin/teams/<id>/sync            → Sync team from Graph
  POST /admin/teams/sync-all             → Sync all teams from Graph
"""
import logging

from flask import (
    Blueprint, render_template, request,
    jsonify, redirect, url_for, flash,
)
from flask_login import login_required, current_user

from app.utils.decorators import gui_admin_required, _get_ip
from app.models.team import Team, Channel
from app.models.audit import AuditLog
from app.extensions import db
from app.forms.team_forms import CreateTeamForm, CreateChannelForm

logger = logging.getLogger(__name__)

teams_bp = Blueprint(
    "teams", __name__,
    template_folder="../templates/teams",
    url_prefix="/admin/teams",
)


@teams_bp.route("/", methods=["GET"])
@login_required
def list_teams():
    """List all teams with search and filter."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    search = request.args.get("q", "").strip()
    visibility = request.args.get("visibility", "").strip()

    q = Team.query
    if search:
        q = q.filter(Team.display_name.ilike(f"%{search}%"))
    if visibility:
        q = q.filter(Team.visibility == visibility)

    q = q.order_by(Team.display_name.asc())
    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    teams = q.offset((page - 1) * per_page).limit(per_page).all()

    stats = {
        "total":    Team.query.count(),
        "active":   Team.query.filter_by(is_archived=False).count(),
        "archived": Team.query.filter_by(is_archived=True).count(),
        "public":   Team.query.filter_by(visibility="public").count(),
        "private":  Team.query.filter_by(visibility="private").count(),
    }

    return render_template(
        "list.html",
        teams=teams,
        stats=stats,
        search=search,
        visibility_filter=visibility,
        page=page,
        pages=pages,
        total=total,
    )


@teams_bp.route("/<int:team_id>", methods=["GET"])
@login_required
def team_detail(team_id: int):
    """Team detail page with channels."""
    team = Team.query.get_or_404(team_id)
    channels = team.channels.order_by(Channel.display_name.asc()).all()
    create_channel_form = CreateChannelForm()
    return render_template(
        "detail.html",
        team=team,
        channels=channels,
        form=create_channel_form,
    )


@teams_bp.route("/create", methods=["GET", "POST"])
@login_required
@gui_admin_required
def create_team():
    """Create a new team via Graph API."""
    form = CreateTeamForm()
    if form.validate_on_submit():
        try:
            from app.services.graph_client import graph_client
            result = graph_client.create_team(
                display_name=form.display_name.data,
                description=form.description.data or "",
                visibility=form.visibility.data,
                owner_id=form.owner_id.data or "",
            )
            AuditLog.write(
                action="CREATE",
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role.value,
                ip_address=_get_ip(),
                resource_type="team",
                resource_name=form.display_name.data,
                status="success",
            )
            flash(f"Team '{form.display_name.data}' creation initiated.", "success")
            return redirect(url_for("teams.list_teams"))
        except Exception as exc:
            logger.error(f"[Teams] Create failed: {exc}")
            flash(f"Failed to create team: {exc}", "danger")

    return render_template("form.html", form=form, action="create")


@teams_bp.route("/<int:team_id>/archive", methods=["POST"])
@login_required
@gui_admin_required
def archive_team(team_id: int):
    """Archive a team."""
    team = Team.query.get_or_404(team_id)
    try:
        from app.services.graph_client import graph_client
        graph_client.archive_team(team.ms_team_id)
        team.is_archived = True
        db.session.commit()
        AuditLog.write(
            action="ARCHIVE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="team",
            resource_name=team.display_name,
            status="success",
        )
        flash(f"Team '{team.display_name}' archived.", "success")
    except Exception as exc:
        flash(f"Archive failed: {exc}", "danger")

    return redirect(url_for("teams.team_detail", team_id=team_id))


@teams_bp.route("/<int:team_id>/unarchive", methods=["POST"])
@login_required
@gui_admin_required
def unarchive_team(team_id: int):
    """Unarchive a team."""
    team = Team.query.get_or_404(team_id)
    try:
        from app.services.graph_client import graph_client
        graph_client.unarchive_team(team.ms_team_id)
        team.is_archived = False
        db.session.commit()
        AuditLog.write(
            action="UNARCHIVE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="team",
            resource_name=team.display_name,
            status="success",
        )
        flash(f"Team '{team.display_name}' unarchived.", "success")
    except Exception as exc:
        flash(f"Unarchive failed: {exc}", "danger")

    return redirect(url_for("teams.team_detail", team_id=team_id))


@teams_bp.route("/<int:team_id>/delete", methods=["POST"])
@login_required
@gui_admin_required
def delete_team(team_id: int):
    """Delete a team."""
    team = Team.query.get_or_404(team_id)
    try:
        from app.services.graph_client import graph_client
        graph_client.delete_team(team.ms_team_id)
        name = team.display_name
        db.session.delete(team)
        db.session.commit()
        AuditLog.write(
            action="DELETE",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="team",
            resource_name=name,
            status="success",
        )
        flash(f"Team '{name}' deleted.", "success")
    except Exception as exc:
        flash(f"Delete failed: {exc}", "danger")
        return redirect(url_for("teams.team_detail", team_id=team_id))

    return redirect(url_for("teams.list_teams"))


@teams_bp.route("/<int:team_id>/channels/create", methods=["POST"])
@login_required
@gui_admin_required
def create_channel(team_id: int):
    """Create a channel in a team."""
    team = Team.query.get_or_404(team_id)
    form = CreateChannelForm()
    if form.validate_on_submit():
        try:
            from app.services.graph_client import graph_client
            graph_client.create_channel(
                team_id=team.ms_team_id,
                display_name=form.display_name.data,
                description=form.description.data or "",
                membership_type=form.membership_type.data,
            )
            AuditLog.write(
                action="CREATE",
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role.value,
                ip_address=_get_ip(),
                resource_type="channel",
                resource_name=form.display_name.data,
                status="success",
            )
            flash(f"Channel '{form.display_name.data}' created.", "success")
        except Exception as exc:
            flash(f"Create channel failed: {exc}", "danger")

    return redirect(url_for("teams.team_detail", team_id=team_id))


@teams_bp.route("/sync-all", methods=["POST"])
@login_required
@gui_admin_required
def sync_all_teams():
    """Sync all teams from Graph API."""
    try:
        from app.services.graph_client import graph_client
        from datetime import datetime, timezone

        graph_teams = graph_client.list_teams()
        synced = 0

        for gt in graph_teams:
            team = Team.query.filter_by(ms_team_id=gt["id"]).first()
            if team is None:
                team = Team(ms_team_id=gt["id"])
                db.session.add(team)

            team.display_name   = gt.get("displayName", "")
            team.description    = gt.get("description", "")
            team.visibility     = gt.get("visibility", "private")
            team.mail_nickname  = gt.get("mailNickname", "")
            team.last_synced_at = datetime.now(timezone.utc)
            synced += 1

        db.session.commit()
        AuditLog.write(
            action="SYNC",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            ip_address=_get_ip(),
            resource_type="team",
            payload_after={"synced_count": synced},
            status="success",
        )
        flash(f"Synced {synced} teams from Microsoft 365.", "success")
    except Exception as exc:
        logger.error(f"[Teams] Sync failed: {exc}")
        flash(f"Sync failed: {exc}", "danger")

    return redirect(url_for("teams.list_teams"))
