# Copyright (c) 2026 Oscar Lohse

"""Synchronize RefCalendar events with the user's primary Google Calendar."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, TypeGuard

import requests
from app_paths import APPLICATION_DIRECTORY, TOKEN_FILE
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

if TYPE_CHECKING:
    from game_to_json import GoogleCalendarEvent

_OAUTH_CLIENT_FILE = APPLICATION_DIRECTORY / "credentials.json"
_TOKEN_FILE = TOKEN_FILE
_CALENDAR_ID = "primary"
_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]
_USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
_TOKEN_REVOKE_URL = "https://oauth2.googleapis.com/revoke"  # noqa: S105
_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_CONFLICT = 409


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
    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=".token-",
        dir=_TOKEN_FILE.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as token_file:
            token_file.write(credentials.to_json())
        temporary_path.replace(_TOKEN_FILE)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _read_saved_credentials(*, allow_authorization: bool) -> Credentials | None:
    if _TOKEN_FILE.is_file():
        try:
            credentials = Credentials.from_authorized_user_file(str(_TOKEN_FILE))
        except (OSError, ValueError) as exc:
            if not allow_authorization:
                msg = "Die gespeicherten Google-Anmeldedaten sind ungültig. Verbinde das Konto erneut."
                raise GoogleCalendarSyncError(msg) from exc
            return None
        else:
            _TOKEN_FILE.chmod(0o600)
            return credentials
    return None


def _credentials_are_usable(credentials: Credentials | None) -> TypeGuard[Credentials]:
    return (
        credentials is not None
        and credentials.valid
        and credentials.has_scopes(_SCOPES)
    )


def _refresh_saved_credentials(
    credentials: Credentials,
    *,
    allow_authorization: bool,
) -> Credentials | None:
    try:
        credentials.refresh(Request())
    except GoogleAuthError as exc:
        if not allow_authorization:
            msg = "Die Google-Sitzung ist abgelaufen. Verbinde das Google-Konto erneut."
            raise GoogleCalendarSyncError(msg) from exc
        return None
    if _credentials_are_usable(credentials):
        _save_credentials(credentials)
    return credentials


def _authorize_google_account(*, open_browser: bool) -> Credentials:
    if not _OAUTH_CLIENT_FILE.is_file():
        msg = (
            "Die OAuth-Konfigurationsdatei credentials.json fehlt im Projektordner. "
            "Lege dort einen OAuth-Client vom Typ „Desktop-App“ ab."
        )
        raise GoogleCalendarSyncError(msg)
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(_OAUTH_CLIENT_FILE),
            _SCOPES,
        )
        credentials = _run_oauth_flow(flow, open_browser=open_browser)
    except (OSError, ValueError, GoogleAuthError) as exc:
        msg = f"Die Google-Anmeldung ist fehlgeschlagen: {exc}. Bitte erneut versuchen."
        raise GoogleCalendarSyncError(msg) from None

    if not _credentials_are_usable(credentials):
        msg = "Google hat keine gültige Anmeldung oder nicht alle erforderlichen Berechtigungen zurückgegeben."
        raise GoogleCalendarSyncError(msg)
    _save_credentials(credentials)
    return credentials


def _load_credentials(
    *,
    open_browser: bool = False,
    allow_authorization: bool = True,
) -> Credentials:
    credentials = _read_saved_credentials(allow_authorization=allow_authorization)
    if _credentials_are_usable(credentials):
        return credentials
    if credentials is not None and credentials.expired and credentials.refresh_token:
        credentials = _refresh_saved_credentials(
            credentials,
            allow_authorization=allow_authorization,
        )
        if _credentials_are_usable(credentials):
            return credentials

    if not allow_authorization:
        msg = "Das Google-Konto muss erneut verbunden werden, um die benötigten Berechtigungen zu erteilen."
        raise GoogleCalendarSyncError(msg)
    return _authorize_google_account(open_browser=open_browser)


def _fetch_google_account_email(credentials: Credentials) -> str:
    try:
        with AuthorizedSession(credentials) as session:
            response = session.get(_USER_INFO_URL, timeout=30)
            response.raise_for_status()
            profile = response.json()
    except (GoogleAuthError, requests.RequestException, ValueError) as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in {_HTTP_UNAUTHORIZED, _HTTP_FORBIDDEN}:
            msg = "Google konnte das Konto nicht bestätigen. Verbinde das Google-Konto erneut."
        elif status is not None:
            msg = f"Die Google-Kontoinformation konnte nicht geladen werden (HTTP {status})."
        else:
            msg = "Die Google-Kontoinformation konnte nicht geladen werden. Prüfe die Internetverbindung."
        raise GoogleCalendarSyncError(msg) from None

    if not isinstance(profile, dict):
        msg = "Google hat ein ungültiges Kontoprofil zurückgegeben."
        raise GoogleCalendarSyncError(msg)
    email = profile.get("email")
    if not isinstance(email, str) or not email.strip():
        msg = "Google hat keine E-Mail-Adresse für dieses Konto zurückgegeben."
        raise GoogleCalendarSyncError(msg)
    return email.strip()


def get_google_account_email() -> str | None:
    """Return the connected Google account email without starting authorization."""
    if not _TOKEN_FILE.is_file():
        return None
    credentials = _load_credentials(allow_authorization=False)
    return _fetch_google_account_email(credentials)


def has_google_credentials() -> bool:
    """Return whether a local Google credential file exists."""
    return _TOKEN_FILE.is_file()


def connect_google_account() -> str:
    """Authorize a Google account and return its email address."""
    credentials = _load_credentials(open_browser=True)
    return _fetch_google_account_email(credentials)


def disconnect_google_account() -> str | None:
    """Remove local credentials and attempt to revoke the Google authorization."""
    if not _TOKEN_FILE.is_file():
        return "Es waren keine lokalen Google-Anmeldedaten vorhanden."

    warning = None
    try:
        credentials = Credentials.from_authorized_user_file(str(_TOKEN_FILE), _SCOPES)
    except (OSError, ValueError):
        warning = "Google konnte die Berechtigung nicht widerrufen, da die gespeicherten Anmeldedaten ungültig waren."
    else:
        token = credentials.refresh_token or credentials.token
        if not token:
            warning = "Google konnte die Berechtigung nicht widerrufen, da kein gültiges Token vorhanden war."
        else:
            try:
                response = requests.post(
                    _TOKEN_REVOKE_URL,
                    data={"token": token},
                    timeout=30,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None:
                    warning = f"Google konnte die Berechtigung nicht widerrufen (HTTP {status})."
                else:
                    warning = "Google konnte die Berechtigung nicht widerrufen. Prüfe die Internetverbindung."

    try:
        _TOKEN_FILE.unlink(missing_ok=True)
    except OSError as exc:
        msg = "Die Google-Berechtigung wurde möglicherweise widerrufen, aber die lokale Anmeldung konnte nicht gelöscht werden."
        raise GoogleCalendarSyncError(msg) from exc
    return warning


def _calendar_api_error(operation: str, error: HttpError) -> GoogleCalendarSyncError:
    status = error.resp.status
    if status == _HTTP_UNAUTHORIZED:
        message = "Die Google-Anmeldung ist ungültig oder abgelaufen."
    elif status == _HTTP_FORBIDDEN:
        message = "Google hat den Zugriff verweigert. Prüfe die Kalenderberechtigung und ob die Google Calendar API aktiviert ist."
    else:
        message = "Google Calendar konnte den Vorgang nicht ausführen."
    return GoogleCalendarSyncError(f"{message} (HTTP {status}, Vorgang: {operation}).")


def _build_calendar_service(
    *,
    open_browser: bool = False,
    allow_authorization: bool = True,
) -> Resource:
    credentials = _load_credentials(
        open_browser=open_browser,
        allow_authorization=allow_authorization,
    )
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
        msg = "Zugriffstest"
        raise _calendar_api_error(msg, exc) from None


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
        msg = "Termin aktualisieren"
        raise _calendar_api_error(msg, exc) from None


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
            if exc.resp.status != _HTTP_NOT_FOUND:
                msg = "Vorhandenen Termin prüfen"
                raise _calendar_api_error(msg, exc) from None
            try:
                service.events().insert(
                    calendarId=_CALENDAR_ID,
                    body=event,
                ).execute()
            except HttpError as insert_error:
                if insert_error.resp.status != _HTTP_CONFLICT:
                    msg_0 = "Termin erstellen"
                    raise _calendar_api_error(msg_0, insert_error) from None
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
    allow_authorization: bool = True,
) -> tuple[int, int]:
    """Create missing events and update existing ones in the primary calendar."""
    service = _build_calendar_service(
        open_browser=open_browser,
        allow_authorization=allow_authorization,
    )
    return _upsert_events(service, events)
