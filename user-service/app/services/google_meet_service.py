"""
Create real Google Meet links via Calendar API (event + conferenceData).

Requires one of:
  - OAuth: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
  - Workspace SA + DWD: GOOGLE_APPLICATION_CREDENTIALS (or GOOGLE_SERVICE_ACCOUNT_JSON)
    and GMEET_DELEGATED_USER (user email to impersonate)

Set GMEET_ENABLED=true and grant Calendar scope to the OAuth client / service account.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def _gmeet_enabled() -> bool:
    return os.getenv("GMEET_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _oauth_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    cid = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    sec = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    ref = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
    if not (cid and sec and ref):
        return None
    creds = Credentials(
        None,
        refresh_token=ref,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cid,
        client_secret=sec,
        scopes=[CALENDAR_SCOPE],
    )
    creds.refresh(Request())
    return creds


def _service_account_credentials():
    from google.oauth2 import service_account

    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    subject = os.getenv("GMEET_DELEGATED_USER", "").strip()
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not subject:
        return None
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=[CALENDAR_SCOPE],
            subject=subject,
        )
    if path and os.path.isfile(path):
        return service_account.Credentials.from_service_account_file(
            path,
            scopes=[CALENDAR_SCOPE],
            subject=subject,
        )
    return None


def _calendar_credentials():
    sa = _service_account_credentials()
    if sa:
        return sa
    return _oauth_credentials()


def _meet_uri_from_event(event: dict[str, Any]) -> str | None:
    link = event.get("hangoutLink")
    if isinstance(link, str) and link.startswith("http"):
        return link
    conf = event.get("conferenceData") or {}
    for ep in conf.get("entryPoints") or []:
        if ep.get("entryPointType") == "video":
            uri = ep.get("uri")
            if isinstance(uri, str) and uri.startswith("http"):
                return uri
    return None


def create_google_meet_link(
    *,
    summary: str,
    start: datetime,
    end: datetime,
    attendee_emails: list[str],
    description: str | None = None,
) -> str | None:
    """
    Returns a https://meet.google.com/... URL or None if disabled / misconfigured / API error.
    """
    if not _gmeet_enabled():
        return None

    creds = _calendar_credentials()
    if not creds:
        log.warning(
            "GMEET_ENABLED but no Google credentials "
            "(set OAuth trio or service account + GMEET_DELEGATED_USER)"
        )
        return None

    try:
        from googleapiclient.discovery import build
    except ImportError:
        log.warning("google-api-python-client not installed; skipping Meet creation")
        return None

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    calendar_id = os.getenv("GMEET_CALENDAR_ID", "primary").strip() or "primary"

    attendees = [{"email": e.strip()} for e in attendee_emails if e and "@" in e]

    body: dict[str, Any] = {
        "summary": summary[:1024],
        "start": {
            "dateTime": start.isoformat().replace("+00:00", "Z"),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end.isoformat().replace("+00:00", "Z"),
            "timeZone": "UTC",
        },
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    if description:
        body["description"] = description[:8000]
    if attendees:
        body["attendees"] = attendees

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        event = (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=body,
                conferenceDataVersion=1,
                sendUpdates="none",
            )
            .execute()
        )
        uri = _meet_uri_from_event(event)
        if uri:
            return uri
        log.warning("Calendar event created but no Meet URI in response: %s", event.get("id"))
    except Exception as exc:  # noqa: BLE001
        log.warning("Google Meet creation failed: %s", exc)
    return None


def resolve_session_meeting_url(
    *,
    session_id,
    fallback_url: str,
    slot_start: datetime,
    slot_end: datetime,
    mentor_email: str | None,
    mentee_email: str | None,
) -> str:
    """
    Try Google Meet; on failure return fallback_url (placeholder).
    """
    summary = "Mentoring session"
    emails = [e for e in (mentor_email, mentee_email) if e]
    desc = f"Session id: {session_id}"
    meet = create_google_meet_link(
        summary=summary,
        start=slot_start,
        end=slot_end,
        attendee_emails=emails,
        description=desc,
    )
    return meet if meet else fallback_url
