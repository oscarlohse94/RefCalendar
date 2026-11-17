"""Parse DHB assignment HTML into RefCalendar data."""

from __future__ import annotations

import re
from collections import Counter

from bs4 import BeautifulSoup, Tag
from game_data import Game, Referee


class GameParseError(RuntimeError):
    """Raised when the returned HTML does not match the expected DHB structure."""


_LABEL_SPACE_RE = re.compile(r"\s+")
_MIN_TABLE_CELLS = 2
_REFEREE_ROLES = {
    "sr1": "SR1",
    "sr2": "SR2",
    "beo": "OBSERVER",
    "beobachter": "OBSERVER",
}
_CONTACT_LABELS = {"tel.", "tel", "mobil", "e-mail", "email"}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _LABEL_SPACE_RE.sub(" ", value).strip()
    return cleaned or None


def _cell_text(cell: Tag) -> str | None:
    return _clean_text(cell.get_text(" ", strip=True))


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""
    return _LABEL_SPACE_RE.sub(" ", value).strip().rstrip(":").casefold()


def _table_rows(table: Tag) -> list[tuple[str, Tag]]:
    rows = []
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) >= _MIN_TABLE_CELLS:
            rows.append((_normalize_label(_cell_text(cells[0])), cells[1]))
    return rows


def _value_for(rows: list[tuple[str, Tag]], *labels: str) -> str | None:
    accepted_labels = set(labels)
    return next(
        (_cell_text(cell) for label, cell in rows if label in accepted_labels),
        None,
    )


def _required_value(value: str | None, field: str, game_id: int) -> str:
    if not value:
        msg = f"Spiel {game_id} ist unvollständig; Feld {field} fehlt."
        raise GameParseError(msg)
    return value


def _cell_for(rows: list[tuple[str, Tag]], label: str) -> Tag | None:
    return next((cell for row_label, cell in rows if row_label == label), None)


def _contact_value(cell: Tag, kind: str) -> str | None:
    """Read contact details from visible text, with the href as a fallback."""
    visible = _cell_text(cell)
    link = cell.find("a", href=True)
    href = str(link.get("href", "")).strip() if link else ""

    if visible:
        return visible
    if kind in {"phone", "mobile"} and href.casefold().startswith("tel:"):
        return _clean_text(href[4:])
    if kind == "email" and href.casefold().startswith("mailto:"):
        return _clean_text(href[7:].split("?", 1)[0])
    return None


def _extract_venue(cell: Tag) -> str:
    lines = cell.get_text("\n", strip=True).splitlines()
    venue = "\n".join(line.strip() for line in lines if line.strip())
    return venue.split("///", maxsplit=1)[0].rstrip()


def _parse_referees(
    rows: list[tuple[str, Tag]],
) -> tuple[Referee | None, Referee | None, Referee | None]:
    sr1: Referee | None = None
    sr2: Referee | None = None
    observer: Referee | None = None
    current_referee: Referee | None = None

    for label, cell in rows:
        role = _REFEREE_ROLES.get(label)
        if role:
            name = _cell_text(cell)
            if not name:
                msg = f"Der Name für {role} fehlt."
                raise GameParseError(msg)
            current_referee = Referee(role=role, name=name)
            if role == "SR1":
                sr1 = current_referee
            elif role == "SR2":
                sr2 = current_referee
            else:
                observer = current_referee
        elif current_referee is not None and label in _CONTACT_LABELS:
            if label in {"tel.", "tel"}:
                current_referee.phone = _contact_value(cell, "phone")
            elif label == "mobil":
                current_referee.mobile = _contact_value(cell, "mobile")
            else:
                current_referee.mail = _contact_value(cell, "email")
        else:
            current_referee = None

    return sr1, sr2, observer


def _parse_date_time(value: str, game_id: int) -> tuple[str, str]:
    date_match = re.search(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b", value)
    time_match = re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", value)
    if not date_match or not time_match:
        msg = f"Datum oder Uhrzeit von Spiel {game_id} konnte nicht erkannt werden."
        raise GameParseError(msg)
    return date_match.group(0), time_match.group(0)


def _parse_match_item(item: Tag) -> Game | None:
    table = item.select_one(".accordion-body table") or item.find("table")
    if table is None:
        return None

    rows = _table_rows(table)
    game_id_text = _value_for(rows, "spielnr.", "spielnr")
    if not game_id_text:
        return None
    try:
        game_id = int(game_id_text)
    except ValueError:
        msg = "Die Spielnummer ist keine gültige Ganzzahl."
        raise GameParseError(msg) from None

    league = _required_value(_value_for(rows, "liga"), "Liga", game_id)
    date_text = _required_value(
        next((_cell_text(cell) for label, cell in rows if label.startswith("datum")), None),
        "Datum",
        game_id,
    )
    home_team = _required_value(_value_for(rows, "heim"), "Heimteam", game_id)
    away_team = _required_value(_value_for(rows, "gast"), "Gastteam", game_id)
    venue_cell = _cell_for(rows, "vo")
    location = _required_value(
        _extract_venue(venue_cell) if venue_cell else None,
        "Spielort",
        game_id,
    )

    date, time = _parse_date_time(date_text, game_id)
    referees = _parse_referees(rows)
    return Game(
        game_id=game_id,
        league=league,
        date=date,
        time=time,
        home_team=home_team,
        away_team=away_team,
        location=location,
        referee=referees,
    )


def parse_games(html: str) -> list[Game]:
    """Parse game assignments from a DHB HTML response."""
    soup = BeautifulSoup(html, "html.parser")
    games = []
    for item in soup.select("div.accordion-item"):
        game = _parse_match_item(item)
        if game is not None:
            games.append(game)

    if not games:
        page_title = soup.title.get_text(" ", strip=True) if soup.title else "unbekannt"
        msg = (
            "Keine Spielansetzungen in der erwarteten HTML-Struktur gefunden. "
            f"Seitentitel: {page_title!r}. Möglicherweise wurde eine Login- oder Fehlerseite geladen."
        )
        raise GameParseError(msg)

    duplicates = sorted(
        game_id
        for game_id, count in Counter(game.game_id for game in games).items()
        if count > 1
    )
    if duplicates:
        msg_0 = f"Doppelte Spielnummern in der Antwort: {', '.join(map(str, duplicates))}"
        raise GameParseError(msg_0)

    return games
