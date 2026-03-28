"""
Cisco Expressway / VCS REST API Client
=========================================
Uses the Expressway REST API for node, zone, and traversal management.
"""
import logging
from typing import Optional

import requests
import urllib3
from requests.auth import HTTPBasicAuth

from app.models.app_config import AppConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class ExpresswayClient:
    """Cisco Expressway / VCS REST client."""

    API_BASE = "https://{host}/api/provisioning"

    def __init__(self, app=None):
        self._app = app
        self._session = None

    def _get_config(self) -> dict:
        try:
            host = AppConfig.get("expressway_host")
            if host:
                return {
                    "host": host,
                    "username": AppConfig.get("expressway_username"),
                    "password": AppConfig.get("expressway_password"),
                    "verify_ssl": AppConfig.get("expressway_verify_ssl", "false") == "true",
                }
        except Exception:
            pass
        if self._app:
            return {
                "host": self._app.config.get("EXPRESSWAY_HOST", ""),
                "username": self._app.config.get("EXPRESSWAY_USERNAME", ""),
                "password": self._app.config.get("EXPRESSWAY_PASSWORD", ""),
                "verify_ssl": self._app.config.get("EXPRESSWAY_VERIFY_SSL", False),
            }
        return {}

    def _get_session(self, config: dict) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = HTTPBasicAuth(config["username"], config["password"])
            self._session.verify = config.get("verify_ssl", False)
            self._session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
        return self._session

    def is_configured(self) -> bool:
        config = self._get_config()
        return bool(config.get("host") and config.get("username"))

    def _url(self, path: str) -> str:
        config = self._get_config()
        return f"{self.API_BASE.format(host=config['host'])}/{path.lstrip('/')}"

    # ── System Status ─────────────────────────────────────────────────────

    def get_system_status(self) -> Optional[dict]:
        config = self._get_config()
        if not config.get("host"):
            return None
        try:
            session = self._get_session(config)
            base = f"https://{config['host']}/api"
            status = {}

            # System info
            try:
                resp = session.get(f"{base}/system/information", timeout=30)
                if resp.ok:
                    status["system_info"] = resp.json()
            except Exception:
                pass

            # Uptime / status
            try:
                resp = session.get(f"{base}/system/status", timeout=30)
                if resp.ok:
                    status["status"] = resp.json()
            except Exception:
                pass

            return status or None
        except Exception as e:
            logger.error(f"Expressway get_system_status failed: {e}")
            return None

    # ── Zones ─────────────────────────────────────────────────────────────

    def list_zones(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(
                f"https://{config['host']}/api/provisioning/zones",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            zones = data.get("Zone", data.get("zone", []))
            return zones if isinstance(zones, list) else [zones]
        except Exception as e:
            logger.error(f"Expressway list_zones failed: {e}")
            return []

    def get_zone(self, zone_name: str) -> Optional[dict]:
        config = self._get_config()
        try:
            session = self._get_session(config)
            resp = session.get(
                f"https://{config['host']}/api/provisioning/zones/{zone_name}",
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Expressway get_zone({zone_name}) failed: {e}")
            return None

    # ── Search Rules ──────────────────────────────────────────────────────

    def list_search_rules(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(
                f"https://{config['host']}/api/provisioning/searchrules",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            rules = data.get("SearchRule", data.get("searchrule", []))
            return rules if isinstance(rules, list) else [rules]
        except Exception as e:
            logger.error(f"Expressway list_search_rules failed: {e}")
            return []

    # ── Registrations ─────────────────────────────────────────────────────

    def get_active_registrations(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(
                f"https://{config['host']}/api/status/registrations",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            regs = data.get("Registration", data.get("registration", []))
            return regs if isinstance(regs, list) else [regs]
        except Exception as e:
            logger.error(f"Expressway get_active_registrations failed: {e}")
            return []

    # ── Active Calls ──────────────────────────────────────────────────────

    def get_active_calls(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(
                f"https://{config['host']}/api/status/calls",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            calls = data.get("Call", data.get("call", []))
            return calls if isinstance(calls, list) else [calls]
        except Exception as e:
            logger.error(f"Expressway get_active_calls failed: {e}")
            return []

    # ── Alarms ────────────────────────────────────────────────────────────

    def get_alarms(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(
                f"https://{config['host']}/api/status/alarms",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            alarms = data.get("Alarm", data.get("alarm", []))
            return alarms if isinstance(alarms, list) else [alarms]
        except Exception as e:
            logger.error(f"Expressway get_alarms failed: {e}")
            return []

    # ── Transforms ────────────────────────────────────────────────────────

    def list_transforms(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(
                f"https://{config['host']}/api/provisioning/transforms",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            transforms = data.get("Transform", data.get("transform", []))
            return transforms if isinstance(transforms, list) else [transforms]
        except Exception as e:
            logger.error(f"Expressway list_transforms failed: {e}")
            return []

    # ── Cluster Peers ─────────────────────────────────────────────────────

    def get_cluster_peers(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(
                f"https://{config['host']}/api/status/cluster",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            peers = data.get("Peer", data.get("peer", []))
            return peers if isinstance(peers, list) else [peers]
        except Exception as e:
            logger.error(f"Expressway get_cluster_peers failed: {e}")
            return []


# Module-level singleton
expressway_client = ExpresswayClient()
