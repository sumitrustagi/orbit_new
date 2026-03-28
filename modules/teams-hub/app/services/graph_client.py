"""
Microsoft Graph API client using MSAL for authentication.

Provides a singleton-style helper that acquires tokens via the
client-credentials flow and exposes typed methods for common
Graph operations (users, teams, channels, calls, meetings).
"""
import logging
from typing import Any

import msal
import requests
from flask import current_app

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    """Wrapper around the Microsoft Graph REST API."""

    def __init__(self):
        self._app: msal.ConfidentialClientApplication | None = None
        self._token_cache: dict | None = None

    # -- Auth ----------------------------------------------------------------

    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        """Lazy-initialise the MSAL confidential client."""
        if self._app is None:
            tenant_id = current_app.config.get("MS_TENANT_ID", "")
            client_id = current_app.config.get("MS_CLIENT_ID", "")
            client_secret = current_app.config.get("MS_CLIENT_SECRET", "")

            if not all([tenant_id, client_id, client_secret]):
                raise ValueError(
                    "MS_TENANT_ID, MS_CLIENT_ID and MS_CLIENT_SECRET must be set."
                )

            self._app = msal.ConfidentialClientApplication(
                client_id=client_id,
                client_credential=client_secret,
                authority=f"https://login.microsoftonline.com/{tenant_id}",
            )
        return self._app

    def _get_token(self) -> str:
        """Acquire a token using the client-credentials flow."""
        app = self._get_msal_app()
        scopes = [current_app.config.get(
            "MS_GRAPH_SCOPES", "https://graph.microsoft.com/.default"
        )]

        result = app.acquire_token_for_client(scopes=scopes)
        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown"))
            raise RuntimeError(f"Failed to acquire Graph token: {error}")

        return result["access_token"]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type":  "application/json",
        }

    # -- HTTP helpers --------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{GRAPH_BASE}{path}"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict | None = None) -> dict:
        url = f"{GRAPH_BASE}{path}"
        resp = requests.post(url, headers=self._headers(), json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, data: dict | None = None) -> dict:
        url = f"{GRAPH_BASE}{path}"
        resp = requests.patch(url, headers=self._headers(), json=data, timeout=30)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def _delete(self, path: str) -> None:
        url = f"{GRAPH_BASE}{path}"
        resp = requests.delete(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()

    def _get_paginated(self, path: str, params: dict | None = None) -> list[dict]:
        """Fetch all pages of a paginated Graph response."""
        results = []
        url = f"{GRAPH_BASE}{path}"
        while url:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
            params = None  # nextLink includes params
        return results

    # -- Users ---------------------------------------------------------------

    def list_users(self, top: int = 100) -> list[dict]:
        """List all users in the tenant."""
        return self._get_paginated(
            "/users",
            params={
                "$top": top,
                "$select": "id,displayName,mail,userPrincipalName,"
                           "jobTitle,department,officeLocation,"
                           "businessPhones,assignedLicenses",
            },
        )

    def get_user(self, user_id: str) -> dict:
        """Get a single user by ID or UPN."""
        return self._get(
            f"/users/{user_id}",
            params={
                "$select": "id,displayName,mail,userPrincipalName,"
                           "jobTitle,department,officeLocation,"
                           "businessPhones,assignedLicenses,"
                           "accountEnabled,createdDateTime",
            },
        )

    def update_user(self, user_id: str, data: dict) -> dict:
        """Update user properties."""
        return self._patch(f"/users/{user_id}", data)

    def assign_license(self, user_id: str, sku_id: str) -> dict:
        """Assign a license SKU to a user."""
        return self._post(f"/users/{user_id}/assignLicense", {
            "addLicenses": [{"skuId": sku_id, "disabledPlans": []}],
            "removeLicenses": [],
        })

    def remove_license(self, user_id: str, sku_id: str) -> dict:
        """Remove a license SKU from a user."""
        return self._post(f"/users/{user_id}/assignLicense", {
            "addLicenses": [],
            "removeLicenses": [sku_id],
        })

    def list_subscribed_skus(self) -> list[dict]:
        """List all subscribed SKUs (licenses) for the tenant."""
        return self._get("/subscribedSkus").get("value", [])

    # -- Teams ---------------------------------------------------------------

    def list_teams(self) -> list[dict]:
        """List all teams in the tenant via groups filter."""
        return self._get_paginated(
            "/groups",
            params={
                "$filter": "resourceProvisioningOptions/Any(x:x eq 'Team')",
                "$select": "id,displayName,description,visibility,mail,"
                           "mailNickname,createdDateTime",
            },
        )

    def get_team(self, team_id: str) -> dict:
        """Get team details."""
        return self._get(f"/teams/{team_id}")

    def create_team(self, display_name: str, description: str = "",
                    visibility: str = "private", owner_id: str = "") -> dict:
        """Create a new team."""
        body: dict[str, Any] = {
            "displayName": display_name,
            "description": description,
            "visibility":  visibility,
            "template@odata.bind":
                "https://graph.microsoft.com/v1.0/teamsTemplates('standard')",
        }
        if owner_id:
            body["members"] = [{
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{owner_id}')",
            }]
        return self._post("/teams", body)

    def archive_team(self, team_id: str) -> None:
        """Archive a team."""
        url = f"{GRAPH_BASE}/teams/{team_id}/archive"
        resp = requests.post(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()

    def unarchive_team(self, team_id: str) -> None:
        """Unarchive a team."""
        url = f"{GRAPH_BASE}/teams/{team_id}/unarchive"
        resp = requests.post(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()

    def delete_team(self, team_id: str) -> None:
        """Delete a team (deletes the underlying group)."""
        self._delete(f"/groups/{team_id}")

    def list_team_members(self, team_id: str) -> list[dict]:
        """List all members of a team."""
        return self._get_paginated(f"/teams/{team_id}/members")

    def add_team_member(self, team_id: str, user_id: str,
                        role: str = "member") -> dict:
        """Add a member to a team."""
        roles = [role] if role == "owner" else []
        return self._post(f"/teams/{team_id}/members", {
            "@odata.type": "#microsoft.graph.aadUserConversationMember",
            "roles": roles,
            "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')",
        })

    def remove_team_member(self, team_id: str, membership_id: str) -> None:
        """Remove a member from a team."""
        self._delete(f"/teams/{team_id}/members/{membership_id}")

    # -- Channels ------------------------------------------------------------

    def list_channels(self, team_id: str) -> list[dict]:
        """List all channels in a team."""
        return self._get_paginated(f"/teams/{team_id}/channels")

    def create_channel(self, team_id: str, display_name: str,
                       description: str = "",
                       membership_type: str = "standard") -> dict:
        """Create a new channel in a team."""
        return self._post(f"/teams/{team_id}/channels", {
            "displayName":    display_name,
            "description":    description,
            "membershipType": membership_type,
        })

    def delete_channel(self, team_id: str, channel_id: str) -> None:
        """Delete a channel from a team."""
        self._delete(f"/teams/{team_id}/channels/{channel_id}")

    # -- Meetings ------------------------------------------------------------

    def list_user_events(self, user_id: str, top: int = 50) -> list[dict]:
        """List calendar events (meetings) for a user."""
        return self._get_paginated(
            f"/users/{user_id}/events",
            params={
                "$top": top,
                "$select": "id,subject,organizer,start,end,isOnlineMeeting,"
                           "onlineMeeting,attendees,recurrence",
                "$orderby": "start/dateTime desc",
            },
        )

    def create_online_meeting(self, user_id: str, subject: str,
                               start_time: str, end_time: str) -> dict:
        """Create an online meeting for a user."""
        return self._post(f"/users/{user_id}/onlineMeetings", {
            "subject":    subject,
            "startDateTime": start_time,
            "endDateTime":   end_time,
        })

    def get_online_meeting(self, user_id: str, meeting_id: str) -> dict:
        """Get online meeting details."""
        return self._get(f"/users/{user_id}/onlineMeetings/{meeting_id}")

    # -- Call Queues & Auto Attendants (Teams Voice) -------------------------

    def list_call_queues(self) -> list[dict]:
        """List call queues (requires Teams admin permissions)."""
        return self._get_paginated(
            "/communications/callQueues",
        )

    def get_call_queue(self, queue_id: str) -> dict:
        """Get call queue details."""
        return self._get(f"/communications/callQueues/{queue_id}")

    def list_auto_attendants(self) -> list[dict]:
        """List auto attendants."""
        return self._get_paginated(
            "/communications/autoAttendants",
        )

    def get_auto_attendant(self, attendant_id: str) -> dict:
        """Get auto attendant details."""
        return self._get(f"/communications/autoAttendants/{attendant_id}")

    # -- Phone Numbers -------------------------------------------------------

    def list_phone_numbers(self) -> list[dict]:
        """List phone numbers assigned in the tenant."""
        try:
            return self._get_paginated("/communications/phoneNumbers")
        except requests.HTTPError:
            logger.warning("Phone numbers endpoint not available")
            return []


# Singleton instance
graph_client = GraphClient()
