"""CUCM background sync tasks."""
import logging
from datetime import datetime, timezone

from app.extensions import celery, db
from app.models.cucm import Phone, DevicePool, Partition, CallingSearchSpace, RoutePattern, TranslationPattern, Gateway, Trunk
from app.models.audit import AuditLog
from app.services.axl_client import axl_client

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.cucm_tasks.sync_phones")
def sync_phones():
    """Sync phones from CUCM via AXL."""
    if not axl_client.is_configured():
        logger.info("CUCM not configured, skipping phone sync")
        return

    try:
        axl_phones = axl_client.list_phones()
        synced = 0
        for p in axl_phones:
            name = p.get("name", "")
            if not name:
                continue
            phone = Phone.query.filter_by(name=name).first()
            if phone is None:
                phone = Phone(name=name)
                db.session.add(phone)
            phone.description = p.get("description", "")
            phone.model = p.get("model", "")
            phone.protocol = p.get("protocol", "")
            phone.device_pool = p.get("devicePoolName", {}).get("_value_1", "") if isinstance(p.get("devicePoolName"), dict) else str(p.get("devicePoolName", ""))
            phone.calling_search_space = p.get("callingSearchSpaceName", {}).get("_value_1", "") if isinstance(p.get("callingSearchSpaceName"), dict) else str(p.get("callingSearchSpaceName", ""))
            phone.owner_user_id = p.get("ownerUserName", {}).get("_value_1", "") if isinstance(p.get("ownerUserName"), dict) else str(p.get("ownerUserName", ""))
            phone.location = p.get("locationName", {}).get("_value_1", "") if isinstance(p.get("locationName"), dict) else str(p.get("locationName", ""))
            phone.last_seen = datetime.now(timezone.utc)
            synced += 1

        db.session.commit()
        _log_sync("SYNC_PHONES", f"Synced {synced} phones from CUCM")
        logger.info(f"Synced {synced} phones from CUCM")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Phone sync failed: {e}")


@celery.task(name="app.tasks.cucm_tasks.sync_device_pools")
def sync_device_pools():
    if not axl_client.is_configured():
        return
    try:
        pools = axl_client.list_device_pools()
        synced = 0
        for p in pools:
            name = p.get("name", "")
            if not name:
                continue
            pool = DevicePool.query.filter_by(name=name).first()
            if pool is None:
                pool = DevicePool(name=name)
                db.session.add(pool)
            pool.date_time_group = p.get("dateTimeSettingName", {}).get("_value_1", "") if isinstance(p.get("dateTimeSettingName"), dict) else str(p.get("dateTimeSettingName", ""))
            pool.region = p.get("regionName", {}).get("_value_1", "") if isinstance(p.get("regionName"), dict) else str(p.get("regionName", ""))
            synced += 1
        db.session.commit()
        _log_sync("SYNC_DEVICE_POOLS", f"Synced {synced} device pools")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Device pool sync failed: {e}")


@celery.task(name="app.tasks.cucm_tasks.sync_partitions")
def sync_partitions():
    if not axl_client.is_configured():
        return
    try:
        parts = axl_client.list_partitions()
        synced = 0
        for p in parts:
            name = p.get("name", "")
            if not name:
                continue
            part = Partition.query.filter_by(name=name).first()
            if part is None:
                part = Partition(name=name)
                db.session.add(part)
            part.description = p.get("description", "")
            synced += 1
        db.session.commit()
        _log_sync("SYNC_PARTITIONS", f"Synced {synced} partitions")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Partition sync failed: {e}")


@celery.task(name="app.tasks.cucm_tasks.sync_css")
def sync_css():
    if not axl_client.is_configured():
        return
    try:
        items = axl_client.list_css()
        synced = 0
        for c in items:
            name = c.get("name", "")
            if not name:
                continue
            css = CallingSearchSpace.query.filter_by(name=name).first()
            if css is None:
                css = CallingSearchSpace(name=name)
                db.session.add(css)
            css.description = c.get("description", "")
            synced += 1
        db.session.commit()
        _log_sync("SYNC_CSS", f"Synced {synced} calling search spaces")
    except Exception as e:
        db.session.rollback()
        logger.error(f"CSS sync failed: {e}")


@celery.task(name="app.tasks.cucm_tasks.sync_route_patterns")
def sync_route_patterns():
    if not axl_client.is_configured():
        return
    try:
        items = axl_client.list_route_patterns()
        synced = 0
        for r in items:
            pattern = r.get("pattern", "")
            if not pattern:
                continue
            rp = RoutePattern.query.filter_by(pattern=pattern).first()
            if rp is None:
                rp = RoutePattern(pattern=pattern)
                db.session.add(rp)
            rp.description = r.get("description", "")
            synced += 1
        db.session.commit()
        _log_sync("SYNC_ROUTE_PATTERNS", f"Synced {synced} route patterns")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Route pattern sync failed: {e}")


@celery.task(name="app.tasks.cucm_tasks.sync_gateways")
def sync_gateways():
    if not axl_client.is_configured():
        return
    try:
        items = axl_client.list_gateways()
        synced = 0
        for g in items:
            name = g.get("domainName", "")
            if not name:
                continue
            gw = Gateway.query.filter_by(name=name).first()
            if gw is None:
                gw = Gateway(name=name)
                db.session.add(gw)
            gw.description = g.get("description", "")
            gw.gateway_type = g.get("product", "")
            synced += 1
        db.session.commit()
        _log_sync("SYNC_GATEWAYS", f"Synced {synced} gateways")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Gateway sync failed: {e}")


@celery.task(name="app.tasks.cucm_tasks.sync_trunks")
def sync_trunks():
    if not axl_client.is_configured():
        return
    try:
        items = axl_client.list_trunks()
        synced = 0
        for t in items:
            name = t.get("name", "")
            if not name:
                continue
            trunk = Trunk.query.filter_by(name=name).first()
            if trunk is None:
                trunk = Trunk(name=name)
                db.session.add(trunk)
            trunk.description = t.get("description", "")
            trunk.trunk_type = "SIP"
            synced += 1
        db.session.commit()
        _log_sync("SYNC_TRUNKS", f"Synced {synced} trunks")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Trunk sync failed: {e}")


@celery.task(name="app.tasks.cucm_tasks.sync_all_cucm")
def sync_all_cucm():
    """Run all CUCM sync tasks."""
    sync_phones()
    sync_device_pools()
    sync_partitions()
    sync_css()
    sync_route_patterns()
    sync_gateways()
    sync_trunks()


def _log_sync(action: str, detail: str):
    audit = AuditLog(username="system", action=action, category="cucm", detail=detail)
    db.session.add(audit)
    db.session.commit()
