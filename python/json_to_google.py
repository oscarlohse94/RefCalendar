# Copyright (c) 2026 Oscar Lohse

"""Synchronize RefCalendar events with the user's primary Google Calendar."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

if TYPE_CHECKING:
    from game_to_json import GoogleCalendarEvent

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_OAUTH_CLIENT_FILE = _PROJECT_ROOT / "credentials.json"
_TOKEN_FILE = _PROJECT_ROOT / "token.json"
_CALENDAR_ID = "primary"
_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class GoogleCalendarSyncError(RuntimeError):
    """Raised when Google Calendar authorization or synchronization fails."""


def _run_oauth_flow(
    flow: InstalledAppFlow,
    *,
    open_browser: bool = False,
) -> Credentials:
    flow_logger = logging.getLogger("google_auth_oauthlib.flow")
    previous_level = flow_logger.level
    flow_logger.setLevel(logging.WARNING)
    try:
        return flow.run_local_server(port=0, open_browser=open_browser)
    finally:
        flow_logger.setLevel(previous_level)


def _save_credentials(credentials: Credentials) -> None:
    file_descriptor, temporary_path = tempfile.mkstemp(
        prefix=".token-",
        dir=_PROJECT_ROOT,
        text=True,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as token_file:
            token_file.write(credentials.to_json())
        os.replace(temporary_path, _TOKEN_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _load_credentials(*, open_browser: bool = False) -> Credentials:
    credentials = None
    if _TOKEN_FILE.is_file():
        try:
            credentials = Credentials.from_authorized_user_file(
                str(_TOKEN_FILE),
                _SCOPES,
            )
        except (OSError, ValueError) as exc:
            msg = "Google OAuth token file is invalid. Remove token.json and authorize again."
            raise GoogleCalendarSyncError(msg) from exc
        os.chmod(_TOKEN_FILE, 0o600)

    if credentials is not None and credentials.valid:
        return credentials

    if credentials is not None and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except GoogleAuthError as exc:
            msg = f"Google OAuth token refresh failed ({type(exc).__name__})."
            raise GoogleCalendarSyncError(msg) from None
    else:
        if not _OAUTH_CLIENT_FILE.is_file():
            msg = (
                "Google OAuth client file is missing. Create a Desktop App OAuth "
                "client and save its download as credentials.json in the project root."
            )
            raise GoogleCalendarSyncError(msg)
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(_OAUTH_CLIENT_FILE),
                _SCOPES,
            )
            credentials = _run_oauth_flow(flow, open_browser=open_browser)
        except (OSError, ValueError, GoogleAuthError) as exc:
            msg = f"Google OAuth authorization failed ({type(exc).__name__})."
            raise GoogleCalendarSyncError(msg) from None

    if not credentials.valid:
        msg = "Google OAuth did not return valid credentials."
        raise GoogleCalendarSyncError(msg)
    _save_credentials(credentials)
    return credentials


def _calendar_api_error(operation: str, error: HttpError) -> GoogleCalendarSyncError:
    return GoogleCalendarSyncError(
        f"Google Calendar {operation} failed (HTTP {error.resp.status})."
    )


def _build_calendar_service(*, open_browser: bool = False) -> Resource:
    credentials = _load_credentials(open_browser=open_browser)
    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def test_google_calendar_access() -> None:
    """Authorize and check read access without changing calendar data."""
    service = _build_calendar_service()
    try:
        service.events().list(
            calendarId=_CALENDAR_ID,
            maxResults=1,
            fields="items(id)",
        ).execute()
    except HttpError as exc:
        raise _calendar_api_error("access check", exc) from None


def _patch_event(
    service: Resource,
    event: GoogleCalendarEvent,
) -> None:
    try:
        service.events().patch(
            calendarId=_CALENDAR_ID,
            eventId=event["id"],
            body={key: value for key, value in event.items() if key != "id"},
        ).execute()
    except HttpError as exc:
        raise _calendar_api_error("patch", exc) from None


def _upsert_events(
    service: Resource,
    events: list[GoogleCalendarEvent],
) -> tuple[int, int]:
    created = 0
    updated = 0

    for event in events:
        event_id = event["id"]
        try:
            service.events().get(
                calendarId=_CALENDAR_ID,
                eventId=event_id,
            ).execute()
        except HttpError as exc:
            if exc.resp.status != 404:
                raise _calendar_api_error("lookup", exc) from None
            try:
                service.events().insert(
                    calendarId=_CALENDAR_ID,
                    body=event,
                ).execute()
            except HttpError as insert_error:
                if insert_error.resp.status != 409:
                    raise _calendar_api_error("insert", insert_error) from None
                _patch_event(service, event)
                updated += 1
            else:
                created += 1
        else:
            _patch_event(service, event)
            updated += 1

    return created, updated


def sync_google_calendar_events(
    events: list[GoogleCalendarEvent],
    *,
    open_browser: bool = False,
) -> tuple[int, int]:
    """Create missing events and update existing ones in the primary calendar."""
    service = _build_calendar_service(open_browser=open_browser)
    return _upsert_events(service, events)
