"""
Cisco IM&P (Instant Messaging & Presence) API Client
=======================================================
Uses the IM&P AXL/REST services for user presence and messaging management.
"""
import logging
from typing import Optional

import requests
import urllib3
from requests.auth import HTTPBasicAuth

from app.models.app_config import AppConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class IMPClient:
    """Cisco IM&P REST/SOAP client."""

    API_BASE = "https://{host}:8443"

    def __init__(self, app=None):
        self._app = app
        self._session = None

    def _get_config(self) -> dict:
        try:
            host = AppConfig.get("imp_host")
            if host:
                return {
                    "host": host,
                    "username": AppConfig.get("imp_username"),
                    "password": AppConfig.get("imp_password"),
                    "verify_ssl": AppConfig.get("imp_verify_ssl", "false") == "true",
                }
        except Exception:
            pass
        if self._app:
            return {
                "host": self._app.config.get("IMP_HOST", ""),
                "username": self._app.config.get("IMP_USERNAME", ""),
                "password": self._app.config.get("IMP_PASSWORD", ""),
                "verify_ssl": self._app.config.get("IMP_VERIFY_SSL", False),
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

    # ── Presence Service ──────────────────────────────────────────────────

    def get_user_presence(self, jabber_id: str) -> Optional[dict]:
        config = self._get_config()
        if not config.get("host"):
            return None
        try:
            session = self._get_session(config)
            url = f"{self.API_BASE.format(host=config['host'])}/presence-service/users/{jabber_id}"
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"IMP get_user_presence({jabber_id}) failed: {e}")
            return None

    # ── User Management (via AXL on IM&P node) ───────────────────────────

    def list_imp_users(self) -> list:
        """Fetch IM&P enabled users via the Cisco Unified CM IM and Presence serviceability API."""
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            url = f"{self.API_BASE.format(host=config['host'])}/cucm-uds/users"
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "user" in data:
                users = data["user"]
                return users if isinstance(users, list) else [users]
            return []
        except Exception as e:
            logger.error(f"IMP list_imp_users failed: {e}")
            return []

    def enable_im_for_user(self, user_id: str) -> bool:
        """Enable IM capability for a user."""
        config = self._get_config()
        if not config.get("host"):
            return False
        try:
            session = self._get_session(config)
            url = f"{self.API_BASE.format(host=config['host'])}/cucm-uds/users/{user_id}"
            resp = session.put(url, json={"imAndPresenceEnable": "true"}, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"IMP enable_im_for_user({user_id}) failed: {e}")
            return False

    def disable_im_for_user(self, user_id: str) -> bool:
        """Disable IM capability for a user."""
        config = self._get_config()
        if not config.get("host"):
            return False
        try:
            session = self._get_session(config)
            url = f"{self.API_BASE.format(host=config['host'])}/cucm-uds/users/{user_id}"
            resp = session.put(url, json={"imAndPresenceEnable": "false"}, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"IMP disable_im_for_user({user_id}) failed: {e}")
            return False

    # ── Service Status ────────────────────────────────────────────────────

    def get_service_status(self) -> Optional[dict]:
        """Get IM&P node service status."""
        config = self._get_config()
        if not config.get("host"):
            return None
        try:
            session = self._get_session(config)
            url = f"{self.API_BASE.format(host=config['host'])}/presence-service/status"
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"IMP get_service_status failed: {e}")
            return None

    # ── Cluster Info ──────────────────────────────────────────────────────

    def get_cluster_info(self) -> Optional[dict]:
        """Get IM&P cluster configuration."""
        config = self._get_config()
        if not config.get("host"):
            return None
        try:
            session = self._get_session(config)
            url = f"{self.API_BASE.format(host=config['host'])}/cucm-uds/clusterUser"
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"IMP get_cluster_info failed: {e}")
            return None


# Module-level singleton
imp_client = IMPClient()
