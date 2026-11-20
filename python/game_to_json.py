
"""Convert RefCalendar games to Google Calendar event resources."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, TypedDict
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from game_data import Game, Referee

CALENDAR_TIMEZONE = ZoneInfo("Europe/Berlin")
_LEAGUE_GENDER_RE = re.compile(r"-(H|D)$")
_BUNDESLIGA_CODE_RE = re.compile(r"BL(\d+)")
_REGIONALLIGA_CODE_RE = re.compile(r"RL(?:[NOSW])?")


class EventDateTime(TypedDict):
    """Google Calendar event date/time value."""

    dateTime: str
    timeZone: str


class GoogleCalendarEvent(TypedDict):
    """Subset of a Google Calendar Event resource used by RefCalendar."""

    id: str
    summary: str
    location: str
    description: str
    start: EventDateTime
    end: EventDateTime


def _format_league(league: str) -> str:
    parts = league.upper().split("-")
    gender_match = _LEAGUE_GENDER_RE.search(league.upper())
    if gender_match is None:
        return league

    gender = gender_match.group(1)
    for part in parts:
        bundesliga_match = _BUNDESLIGA_CODE_RE.fullmatch(part)
        if bundesliga_match is not None:
            return f"{bundesliga_match.group(1)}. BL{gender}"
        if part == "OL":
            return f"OL{gender}"
        if _REGIONALLIGA_CODE_RE.fullmatch(part):
            return f"RL{gender}"
    return league


def _parse_game_start(game: Game) -> datetime:
    value = f"{game.date} {game.time}"
    date_format = "%d.%m.%Y %H:%M:%S" if game.time.count(":") == 2 else "%d.%m.%Y %H:%M"
    try:
        return datetime.strptime(value, date_format).replace(tzinfo=CALENDAR_TIMEZONE)
    except ValueError:
        pass
    msg = f"Datum oder Uhrzeit von Spiel {game.game_id} hat ein ungültiges Format."
    raise ValueError(msg)


def _referee_description(label: str, referee: Referee | None) -> str | None:
    if referee is None:
        return None

    details = [referee.name]
    if referee.phone:
        details.append(f"Telefon: {referee.phone}")
    if referee.mobile:
        details.append(f"Mobil: {referee.mobile}")
    if referee.mail:
        details.append(f"Mail: {referee.mail}")
    return f"{label}: {', '.join(details)}"


def _event_datetime(value: datetime) -> EventDateTime:
    return {
        "dateTime": value.isoformat(),
        "timeZone": CALENDAR_TIMEZONE.key,
    }


def game_to_google_calendar_event(game: Game) -> GoogleCalendarEvent:
    """Convert one game to the JSON-compatible shape accepted by Google Calendar."""
    start = _parse_game_start(game)
    end = (
        start.astimezone(timezone.utc) + timedelta(hours=2)
    ).astimezone(CALENDAR_TIMEZONE)

    description_lines = [f"Spielnummer: {game.game_id}"]
    for label, referee in zip(("SR1", "SR2", "Beo"), game.referee, strict=False):
        line = _referee_description(label, referee)
        if line is not None:
            description_lines.append(line)

    return {
        "id": uuid5(
            NAMESPACE_URL,
            f"refcalendar:dhb-game:{game.game_id}",
        ).hex,
        "summary": (
            f"{_format_league(game.league)}: "
            f"{game.home_team} - {game.away_team}"
        ),
        "location": game.location,
        "description": "\n".join(description_lines),
        "start": _event_datetime(start),
        "end": _event_datetime(end),
    }


def games_to_google_calendar_events(
    games: list[Game],
) -> list[GoogleCalendarEvent]:
    """Convert games to a list of Google Calendar event resources."""
    return [game_to_google_calendar_event(game) for game in games]
