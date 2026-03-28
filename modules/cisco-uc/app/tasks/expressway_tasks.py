"""Expressway background sync tasks."""
import logging
from datetime import datetime, timezone

from app.extensions import celery, db
from app.models.expressway import Expressway, Zone
from app.models.audit import AuditLog
from app.services.expressway_client import expressway_client

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.expressway_tasks.sync_expressways")
def sync_expressways():
    if not expressway_client.is_configured():
        logger.info("Expressway not configured, skipping sync")
        return
    try:
        status = expressway_client.get_system_status()
        if not status:
            return

        sys_info = status.get("system_info", {})
        sys_status = status.get("status", {})

        name = sys_info.get("SystemName", sys_info.get("systemName", "Expressway"))
        node = Expressway.query.filter_by(name=name).first()
        if node is None:
            from app.models.app_config import AppConfig
            host = AppConfig.get("expressway_host", "")
            node = Expressway(name=name, host=host, node_type="Core")
            db.session.add(node)

        node.software_version = sys_info.get("SoftwareVersion", sys_info.get("softwareVersion", ""))
        node.serial_number = sys_info.get("SerialNumber", sys_info.get("serialNumber", ""))
        node.hardware_version = sys_info.get("HardwareVersion", sys_info.get("hardwareVersion", ""))
        node.status = "Active"
        node.last_polled = datetime.now(timezone.utc)
        db.session.commit()

        # Sync zones
        zones = expressway_client.list_zones()
        for z in zones:
            zone_name = z.get("Name", z.get("name", ""))
            if not zone_name:
                continue
            zone = Zone.query.filter_by(name=zone_name, expressway_id=node.id).first()
            if zone is None:
                zone = Zone(name=zone_name, expressway_id=node.id)
                db.session.add(zone)
            zone.zone_type = z.get("Type", z.get("type", ""))
            zone.peer_address = z.get("PeerAddress", z.get("peerAddress", ""))
            zone.status = z.get("Status", z.get("status", "Unknown"))

        db.session.commit()
        audit = AuditLog(username="system", action="SYNC_EXPRESSWAYS", category="expressway", detail=f"Synced Expressway {name}")
        db.session.add(audit)
        db.session.commit()
        logger.info(f"Synced Expressway: {name}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Expressway sync failed: {e}")
