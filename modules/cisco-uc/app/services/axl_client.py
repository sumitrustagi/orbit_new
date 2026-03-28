"""
Cisco CUCM AXL (Administrative XML) / RIS / UDS Client
=========================================================
Uses Zeep SOAP client for AXL operations and requests for RIS/UDS REST calls.
Handles phone management, device pools, partitions, CSS, route patterns, gateways, trunks.
"""
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
import urllib3
from requests.auth import HTTPBasicAuth
from zeep import Client as ZeepClient
from zeep.transports import Transport
from zeep.plugins import HistoryPlugin

from app.models.app_config import AppConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class AXLClient:
    """CUCM AXL SOAP + RIS + UDS client."""

    AXL_WSDL_PATH = "https://{host}:8443/axl/schema/{version}/AXLAPI.wsdl"
    RIS_URL       = "https://{host}:8443/realtimeservice2/services/RISService70"
    UDS_BASE      = "https://{host}:8443/cucm-uds"

    def __init__(self, app=None):
        self._app = app
        self._axl_service = None
        self._session = None
        self._history = HistoryPlugin()

    def _get_config(self) -> dict:
        """Read CUCM config from AppConfig DB or Flask config."""
        try:
            host = AppConfig.get("cucm_host")
            if host:
                return {
                    "host": host,
                    "username": AppConfig.get("cucm_username"),
                    "password": AppConfig.get("cucm_password"),
                    "version": AppConfig.get("cucm_version", "14.0"),
                    "verify_ssl": AppConfig.get("cucm_verify_ssl", "false") == "true",
                }
        except Exception:
            pass
        if self._app:
            return {
                "host": self._app.config.get("CUCM_HOST", ""),
                "username": self._app.config.get("CUCM_USERNAME", ""),
                "password": self._app.config.get("CUCM_PASSWORD", ""),
                "version": self._app.config.get("CUCM_VERSION", "14.0"),
                "verify_ssl": self._app.config.get("CUCM_VERIFY_SSL", False),
            }
        return {}

    def _get_session(self, config: dict) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = HTTPBasicAuth(config["username"], config["password"])
            self._session.verify = config.get("verify_ssl", False)
            self._session.headers.update({"Content-Type": "text/xml"})
        return self._session

    def _get_axl_service(self, config: dict):
        if self._axl_service is None:
            wsdl_url = self.AXL_WSDL_PATH.format(host=config["host"], version=config["version"])
            session = self._get_session(config)
            transport = Transport(session=session, timeout=30)
            client = ZeepClient(wsdl=wsdl_url, transport=transport, plugins=[self._history])
            self._axl_service = client.create_service(
                "{http://www.cisco.com/AXLAPIService/}AXLAPIBinding",
                f"https://{config['host']}:8443/axl/"
            )
        return self._axl_service

    def is_configured(self) -> bool:
        config = self._get_config()
        return bool(config.get("host") and config.get("username"))

    # ── Phone Operations ──────────────────────────────────────────────────

    def list_phones(self, search_criteria: Optional[dict] = None, returned_tags: Optional[dict] = None) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            criteria = search_criteria or {"name": "%"}
            tags = returned_tags or {
                "name": "", "description": "", "model": "", "protocol": "",
                "devicePoolName": "", "callingSearchSpaceName": "",
                "ownerUserName": "", "locationName": "",
            }
            result = service.listPhone(searchCriteria=criteria, returnedTags=tags)
            phones = result.get("return", {})
            if phones and "phone" in phones:
                return phones["phone"]
            return []
        except Exception as e:
            logger.error(f"AXL listPhone failed: {e}")
            return []

    def get_phone(self, name: str) -> Optional[dict]:
        config = self._get_config()
        if not config.get("host"):
            return None
        try:
            service = self._get_axl_service(config)
            result = service.getPhone(name=name)
            return result.get("return", {}).get("phone")
        except Exception as e:
            logger.error(f"AXL getPhone({name}) failed: {e}")
            return None

    def add_phone(self, phone_data: dict) -> Optional[str]:
        config = self._get_config()
        try:
            service = self._get_axl_service(config)
            result = service.addPhone(phone=phone_data)
            return result.get("return")
        except Exception as e:
            logger.error(f"AXL addPhone failed: {e}")
            return None

    def update_phone(self, name: str, updates: dict) -> bool:
        config = self._get_config()
        try:
            service = self._get_axl_service(config)
            service.updatePhone(name=name, **updates)
            return True
        except Exception as e:
            logger.error(f"AXL updatePhone({name}) failed: {e}")
            return False

    def remove_phone(self, name: str) -> bool:
        config = self._get_config()
        try:
            service = self._get_axl_service(config)
            service.removePhone(name=name)
            return True
        except Exception as e:
            logger.error(f"AXL removePhone({name}) failed: {e}")
            return False

    # ── Device Pool Operations ────────────────────────────────────────────

    def list_device_pools(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            result = service.listDevicePool(
                searchCriteria={"name": "%"},
                returnedTags={"name": "", "dateTimeSettingName": "", "regionName": "", "srstName": ""}
            )
            pools = result.get("return", {})
            if pools and "devicePool" in pools:
                return pools["devicePool"]
            return []
        except Exception as e:
            logger.error(f"AXL listDevicePool failed: {e}")
            return []

    # ── Partition Operations ──────────────────────────────────────────────

    def list_partitions(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            result = service.listRoutePartition(
                searchCriteria={"name": "%"},
                returnedTags={"name": "", "description": "", "timeScheduleIdName": ""}
            )
            parts = result.get("return", {})
            if parts and "routePartition" in parts:
                return parts["routePartition"]
            return []
        except Exception as e:
            logger.error(f"AXL listRoutePartition failed: {e}")
            return []

    # ── Calling Search Space Operations ───────────────────────────────────

    def list_css(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            result = service.listCss(
                searchCriteria={"name": "%"},
                returnedTags={"name": "", "description": ""}
            )
            css_list = result.get("return", {})
            if css_list and "css" in css_list:
                return css_list["css"]
            return []
        except Exception as e:
            logger.error(f"AXL listCss failed: {e}")
            return []

    # ── Route Pattern Operations ──────────────────────────────────────────

    def list_route_patterns(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            result = service.listRoutePattern(
                searchCriteria={"pattern": "%"},
                returnedTags={"pattern": "", "description": "", "routePartitionName": "", "blockEnable": ""}
            )
            rps = result.get("return", {})
            if rps and "routePattern" in rps:
                return rps["routePattern"]
            return []
        except Exception as e:
            logger.error(f"AXL listRoutePattern failed: {e}")
            return []

    # ── Translation Pattern Operations ────────────────────────────────────

    def list_translation_patterns(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            result = service.listTransPattern(
                searchCriteria={"pattern": "%"},
                returnedTags={"pattern": "", "description": "", "routePartitionName": "", "callingSearchSpaceName": ""}
            )
            tps = result.get("return", {})
            if tps and "transPattern" in tps:
                return tps["transPattern"]
            return []
        except Exception as e:
            logger.error(f"AXL listTransPattern failed: {e}")
            return []

    # ── Gateway Operations ────────────────────────────────────────────────

    def list_gateways(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            result = service.listGateway(
                searchCriteria={"domainName": "%"},
                returnedTags={"domainName": "", "description": "", "product": "", "protocol": ""}
            )
            gws = result.get("return", {})
            if gws and "gateway" in gws:
                return gws["gateway"]
            return []
        except Exception as e:
            logger.error(f"AXL listGateway failed: {e}")
            return []

    # ── Trunk Operations ──────────────────────────────────────────────────

    def list_trunks(self) -> list:
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            result = service.listSipTrunk(
                searchCriteria={"name": "%"},
                returnedTags={"name": "", "description": "", "devicePoolName": "", "callingSearchSpaceName": ""}
            )
            trunks = result.get("return", {})
            if trunks and "sipTrunk" in trunks:
                return trunks["sipTrunk"]
            return []
        except Exception as e:
            logger.error(f"AXL listSipTrunk failed: {e}")
            return []

    # ── RIS (Real-time Information Service) ───────────────────────────────

    def get_phone_registration_status(self, device_names: list) -> list:
        """Query RIS for real-time phone registration status."""
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            session = self._get_session(config)
            ris_url = self.RIS_URL.format(host=config["host"])

            items = "".join(f"<item><Item>{n}</Item></item>" for n in device_names[:1000])
            body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ris="http://schemas.cisco.com/ast/soap">
  <soapenv:Body>
    <ris:selectCmDevice>
      <ris:StateInfo></ris:StateInfo>
      <ris:CmSelectionCriteria>
        <ris:MaxReturnedDevices>1000</ris:MaxReturnedDevices>
        <ris:DeviceClass>Phone</ris:DeviceClass>
        <ris:Model>255</ris:Model>
        <ris:Status>Any</ris:Status>
        <ris:SelectBy>Name</ris:SelectBy>
        <ris:SelectItems>{items}</ris:SelectItems>
      </ris:CmSelectionCriteria>
    </ris:selectCmDevice>
  </soapenv:Body>
</soapenv:Envelope>"""

            resp = session.post(ris_url, data=body, timeout=30)
            resp.raise_for_status()
            return self._parse_ris_response(resp.text)
        except Exception as e:
            logger.error(f"RIS query failed: {e}")
            return []

    def _parse_ris_response(self, xml_text: str) -> list:
        """Parse RIS SOAP response to extract device status."""
        try:
            from lxml import etree
            root = etree.fromstring(xml_text.encode())
            ns = {"ris": "http://schemas.cisco.com/ast/soap"}
            devices = []
            for node in root.iter():
                if "CmDevice" in node.tag:
                    device = {}
                    for child in node:
                        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        device[tag] = child.text
                    if device.get("Name"):
                        devices.append(device)
            return devices
        except Exception as e:
            logger.error(f"RIS parse failed: {e}")
            return []

    # ── SQL Query (executeSQLQuery) ───────────────────────────────────────

    def execute_sql(self, sql: str) -> list:
        """Run a read-only SQL query against CUCM Informix DB via AXL."""
        config = self._get_config()
        if not config.get("host"):
            return []
        try:
            service = self._get_axl_service(config)
            result = service.executeSQLQuery(sql=sql)
            rows = result.get("return", {})
            if rows and "row" in rows:
                return rows["row"]
            return []
        except Exception as e:
            logger.error(f"AXL executeSQLQuery failed: {e}")
            return []


# Module-level singleton
axl_client = AXLClient()
