"""
Cisco Unity Connection REST API Client
=========================================
Uses the Unity Connection REST (CUPI) API for mailbox and user management.
"""
import logging
from typing import Optional

import requests
import urllib3
from requests.auth import HTTPBasicAuth

from app.models.app_config import AppConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class UnityClient:
    """Cisco Unity Connection CUPI REST client."""

    API_BASE = "https://{host}/vmrest"

    def __init__(self, app=None):
        self._app = app
        self._session = None

    def _get_config(self) -> dict:
        try:
            host = AppConfig.get("unity_host")
            if host:
                return {
                    "host": host,
                    "username": AppConfig.get("unity_username"),
                    "password": AppConfig.get("unity_password"),
                    "verify_ssl": AppConfig.get("unity_verify_ssl", "false") == "true",
                }
        except Exception:
            pass
        if self._app:
            return {
                "host": self._app.config.get("UNITY_HOST", ""),
                "username": self._app.config.get("UNITY_USERNAME", ""),
                "password": self._app.config.get("UNITY_PASSWORD", ""),
                "verify_ssl": self._app.config.get("UNITY_VERIFY_SSL", False),
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
                "Connection": "keep-alive",
            })
        return self._session

    def is_configured(self) -> bool:
        config = self._get_config()
        return bool(config.get("host") and config.get("username"))

    def _url(self, path: str) -> str:
        config = self._get_config()
        return f"{self.API_BASE.format(host=config['host'])}/{path.lstrip('/')}"

    # ── Users ─────────────────────────────────────────────────────────────

    def list_users(self, page_size: int = 100, page: int = 1) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            offset = (page - 1) * page_size
            url = self._url(f"users?rowsPerPage={page_size}&pageNumber={page}")
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "User" in data:
                users = data["User"]
                return users if isinstance(users, list) else [users]
            return []
        except Exception as e:
            logger.error(f"Unity list_users failed: {e}")
            return []

    def get_user(self, object_id: str) -> Optional[dict]:
        config = self._get_config()
        if not config.get("host"):
            return None
        try:
            session = self._get_session(config)
            resp = session.get(self._url(f"users/{object_id}"), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Unity get_user({object_id}) failed: {e}")
            return None

    def get_user_by_alias(self, alias: str) -> Optional[dict]:
        config = self._get_config()
        if not config.get("host"):
            return None
        try:
            session = self._get_session(config)
            resp = session.get(self._url(f"users?query=(Alias is {alias})"), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "User" in data:
                users = data["User"]
                if isinstance(users, list):
                    return users[0] if users else None
                return users
            return None
        except Exception as e:
            logger.error(f"Unity get_user_by_alias({alias}) failed: {e}")
            return None

    # ── Mailboxes (Call Handlers) ─────────────────────────────────────────

    def list_call_handlers(self, page_size: int = 100) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(self._url(f"handlers/callhandlers?rowsPerPage={page_size}"), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "Callhandler" in data:
                handlers = data["Callhandler"]
                return handlers if isinstance(handlers, list) else [handlers]
            return []
        except Exception as e:
            logger.error(f"Unity list_call_handlers failed: {e}")
            return []

    def get_call_handler(self, object_id: str) -> Optional[dict]:
        config = self._get_config()
        try:
            session = self._get_session(config)
            resp = session.get(self._url(f"handlers/callhandlers/{object_id}"), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Unity get_call_handler({object_id}) failed: {e}")
            return None

    # ── Voicemail User Mailbox (via user endpoints) ───────────────────────

    def list_user_mailboxes(self, page_size: int = 100) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(self._url(f"users?rowsPerPage={page_size}"), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "User" in data:
                users = data["User"]
                return users if isinstance(users, list) else [users]
            return []
        except Exception as e:
            logger.error(f"Unity list_user_mailboxes failed: {e}")
            return []

    def create_user(self, user_data: dict) -> Optional[str]:
        config = self._get_config()
        try:
            session = self._get_session(config)
            resp = session.post(
                self._url("users?templateAlias=voicemailusertemplate"),
                json=user_data, timeout=30,
            )
            resp.raise_for_status()
            location = resp.headers.get("Location", "")
            return location.split("/")[-1] if location else None
        except Exception as e:
            logger.error(f"Unity create_user failed: {e}")
            return None

    def update_user(self, object_id: str, updates: dict) -> bool:
        config = self._get_config()
        try:
            session = self._get_session(config)
            resp = session.put(self._url(f"users/{object_id}"), json=updates, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Unity update_user({object_id}) failed: {e}")
            return False

    def delete_user(self, object_id: str) -> bool:
        config = self._get_config()
        try:
            session = self._get_session(config)
            resp = session.delete(self._url(f"users/{object_id}"), timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Unity delete_user({object_id}) failed: {e}")
            return False

    # ── PIN / Password Reset ──────────────────────────────────────────────

    def reset_user_pin(self, object_id: str, new_pin: str) -> bool:
        config = self._get_config()
        try:
            session = self._get_session(config)
            resp = session.put(
                self._url(f"users/{object_id}/credential/pin"),
                json={"Credentials": new_pin}, timeout=30,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Unity reset_user_pin({object_id}) failed: {e}")
            return False

    # ── Class of Service ──────────────────────────────────────────────────

    def list_cos(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            resp = session.get(self._url("cos"), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "Cos" in data:
                cos = data["Cos"]
                return cos if isinstance(cos, list) else [cos]
            return []
        except Exception as e:
            logger.error(f"Unity list_cos failed: {e}")
            return []

    # ── Server Info ───────────────────────────────────────────────────────

    def get_server_info(self) -> Optional[dict]:
        config = self._get_config()
        if not config.get("host"):
            return None
        try:
            session = self._get_session(config)
            resp = session.get(self._url("cluster"), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Unity get_server_info failed: {e}")
            return None


# Module-level singleton
unity_client = UnityClient()
