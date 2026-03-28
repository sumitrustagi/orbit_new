"""
Background tasks for syncing Microsoft Teams data via Graph API.
"""
import logging
from datetime import datetime, timezone

from app.extensions import celery, db
from app.models.team import Team, Channel
from app.models.call_queue import CallQueue, AutoAttendant
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.teams_sync.sync_all_teams", bind=True, max_retries=3)
def sync_all_teams(self):
    """Sync all teams and their channels from Graph API."""
    try:
        from app.services.graph_client import graph_client

        graph_teams = graph_client.list_teams()
        synced_teams = 0
        synced_channels = 0

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
            synced_teams += 1

            # Sync channels for this team
            try:
                graph_channels = graph_client.list_channels(gt["id"])
                for gc in graph_channels:
                    channel = Channel.query.filter_by(ms_channel_id=gc["id"]).first()
                    if channel is None:
                        channel = Channel(ms_channel_id=gc["id"], team_id=team.id)
                        db.session.add(channel)

                    channel.display_name    = gc.get("displayName", "")
                    channel.description     = gc.get("description", "")
                    channel.membership_type = gc.get("membershipType", "standard")
                    channel.last_synced_at  = datetime.now(timezone.utc)
                    synced_channels += 1
            except Exception as exc:
                logger.warning(f"[Sync] Failed to sync channels for team {gt['id']}: {exc}")

        db.session.commit()

        AuditLog.write(
            action="SYNC",
            username="celery",
            resource_type="team",
            payload_after={
                "teams_synced": synced_teams,
                "channels_synced": synced_channels,
            },
            status="success",
        )
        logger.info(f"[Sync] Synced {synced_teams} teams, {synced_channels} channels.")
        return {"teams": synced_teams, "channels": synced_channels}

    except Exception as exc:
        logger.error(f"[Sync] Team sync failed: {exc}")
        AuditLog.write(
            action="SYNC",
            username="celery",
            resource_type="team",
            status="failure",
            status_detail=str(exc),
        )
        raise self.retry(exc=exc, countdown=60)


@celery.task(name="app.tasks.teams_sync.sync_graph_users", bind=True, max_retries=3)
def sync_graph_users(self):
    """Sync users from Microsoft Graph to the local database."""
    try:
        from app.services.graph_client import graph_client
        from app.models.user import User

        graph_users = graph_client.list_users()
        synced = 0

        for gu in graph_users:
            user = User.query.filter_by(ms_user_id=gu["id"]).first()
            if user is None:
                # Only update existing users that have been linked
                continue

            user.ms_upn          = gu.get("userPrincipalName", "")
            user.display_name    = gu.get("displayName", "")
            phones = gu.get("businessPhones", [])
            if phones:
                user.ms_phone_number = phones[0]
            user.ms_location     = gu.get("officeLocation", "")
            synced += 1

        db.session.commit()

        AuditLog.write(
            action="SYNC",
            username="celery",
            resource_type="user",
            payload_after={"users_synced": synced},
            status="success",
        )
        logger.info(f"[Sync] Synced {synced} Graph users.")
        return {"users_synced": synced}

    except Exception as exc:
        logger.error(f"[Sync] User sync failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery.task(name="app.tasks.teams_sync.sync_call_resources", bind=True, max_retries=3)
def sync_call_resources(self):
    """Sync call queues and auto attendants from Graph API."""
    try:
        from app.services.graph_client import graph_client

        queue_count = 0
        attendant_count = 0

        # Sync call queues
        try:
            graph_queues = graph_client.list_call_queues()
            for gq in graph_queues:
                cq = CallQueue.query.filter_by(ms_queue_id=gq["id"]).first()
                if cq is None:
                    cq = CallQueue(ms_queue_id=gq["id"])
                    db.session.add(cq)
                cq.display_name    = gq.get("displayName", "")
                cq.agent_count     = len(gq.get("agents", []))
                cq.last_synced_at  = datetime.now(timezone.utc)
                queue_count += 1
        except Exception as exc:
            logger.warning(f"[Sync] Call queue sync unavailable: {exc}")

        # Sync auto attendants
        try:
            graph_attendants = graph_client.list_auto_attendants()
            for ga in graph_attendants:
                aa = AutoAttendant.query.filter_by(ms_attendant_id=ga["id"]).first()
                if aa is None:
                    aa = AutoAttendant(ms_attendant_id=ga["id"])
                    db.session.add(aa)
                aa.display_name    = ga.get("displayName", "")
                aa.language        = ga.get("languageId", "en-US")
                aa.last_synced_at  = datetime.now(timezone.utc)
                attendant_count += 1
        except Exception as exc:
            logger.warning(f"[Sync] Auto attendant sync unavailable: {exc}")

        db.session.commit()

        AuditLog.write(
            action="SYNC",
            username="celery",
            resource_type="calls",
            payload_after={
                "queues_synced": queue_count,
                "attendants_synced": attendant_count,
            },
            status="success",
        )
        logger.info(f"[Sync] Synced {queue_count} queues, {attendant_count} attendants.")
        return {"queues": queue_count, "attendants": attendant_count}

    except Exception as exc:
        logger.error(f"[Sync] Call resource sync failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
