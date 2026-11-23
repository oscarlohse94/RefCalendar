# Copyright (c) 2026 Oscar Lohse

"""Persist a user's parsed DHB assignments between application runs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from game_data import Game, Referee, User

_CACHE_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache"))
_CACHE_FILE = _CACHE_ROOT / "RefCalendar" / "user-cache.json"
_CACHE_SCHEMA_VERSION = 1
_REFEREE_COUNT = 3


class UserCacheError(RuntimeError):
    """Raised when the cached user data cannot be read or written."""


@dataclass(frozen=True)
class CachedUser:
    """A parsed user and the time its DHB page was fetched."""

    user: User
    fetched_at: datetime


def _source_fingerprint(source_url: str) -> str:
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()


def _serialize_game(game: Game) -> dict[str, object]:
    return {
        "game_id": game.game_id,
        "league": game.league,
        "date": game.date,
        "time": game.time,
        "home_team": game.home_team,
        "away_team": game.away_team,
        "location": game.location,
        "referee": [
            None
            if referee is None
            else {
                "role": referee.role,
                "name": referee.name,
                "mail": referee.mail,
                "phone": referee.phone,
                "mobile": referee.mobile,
            }
            for referee in game.referee
        ],
    }


def save_user_cache(user: User, source_url: str) -> None:
    """Atomically save parsed games without copying the private source URL."""
    cache_directory = _CACHE_FILE.parent
    payload = {
        "schema_version": _CACHE_SCHEMA_VERSION,
        "source_fingerprint": _source_fingerprint(source_url),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "name": user.name,
            "games": [_serialize_game(game) for game in user.games],
        },
    }

    temporary_path = None
    try:
        cache_directory.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_path = tempfile.mkstemp(
            prefix=".user-cache-",
            dir=cache_directory,
        )
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as cache_file:
            json.dump(payload, cache_file, ensure_ascii=False, indent=2)
            cache_file.write("\n")
        Path(temporary_path).replace(_CACHE_FILE)
    except OSError as exc:
        msg = "Der lokale Spiel-Cache konnte nicht gespeichert werden."
        raise UserCacheError(msg) from exc
    finally:
        if temporary_path is not None and Path(temporary_path).exists():
            Path(temporary_path).unlink()


def _require_object(value: object, description: str) -> dict[str, object]:
    if not isinstance(value, dict):
        msg = f"{description} im Cache ist ungültig."
        raise TypeError(msg)
    return value


def _require_text(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        msg = f"Feld {key} im Cache ist ungültig."
        raise TypeError(msg)
    return value


def _optional_text(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        msg = f"Feld {key} im Cache ist ungültig."
        raise ValueError(msg)
    return value


def _parse_referee(value: object) -> Referee | None:
    if value is None:
        return None
    data = _require_object(value, "Schiedsrichter")
    return Referee(
        role=_require_text(data, "role"),
        name=_require_text(data, "name"),
        mail=_optional_text(data, "mail"),
        phone=_optional_text(data, "phone"),
        mobile=_optional_text(data, "mobile"),
    )


def _parse_game(value: object) -> Game:
    data = _require_object(value, "Spiel")
    game_id = data.get("game_id")
    referees = data.get("referee")
    if not isinstance(game_id, int) or isinstance(game_id, bool):
        msg = "Spielnummer im Cache ist ungültig."
        raise TypeError(msg)
    if not isinstance(referees, list) or len(referees) != _REFEREE_COUNT:
        msg_0 = "Schiedsrichterliste im Cache ist ungültig."
        raise ValueError(msg_0)

    return Game(
        game_id=game_id,
        league=_require_text(data, "league"),
        date=_require_text(data, "date"),
        time=_require_text(data, "time"),
        home_team=_require_text(data, "home_team"),
        away_team=_require_text(data, "away_team"),
        location=_require_text(data, "location"),
        referee=(
            _parse_referee(referees[0]),
            _parse_referee(referees[1]),
            _parse_referee(referees[2]),
        ),
    )


def _parse_cached_user(payload: dict[str, object], source_url: str) -> CachedUser | None:
    """Validate and parse cache payload for the configured source URL."""
    if payload.get("schema_version") != _CACHE_SCHEMA_VERSION:
        msg = "Cache-Version wird nicht unterstützt."
        raise ValueError(msg)

    fingerprint = _require_text(payload, "source_fingerprint")
    if fingerprint != _source_fingerprint(source_url):
        return None

    fetched_at = datetime.fromisoformat(_require_text(payload, "fetched_at"))
    if fetched_at.tzinfo is None:
        msg_0 = "Zeitpunkt im Cache hat keine Zeitzone."
        raise ValueError(msg_0)

    user_data = _require_object(payload.get("user"), "Benutzerdaten")
    games_data = user_data.get("games")
    if not isinstance(games_data, list):
        msg_1 = "Spielliste im Cache ist ungültig."
        raise TypeError(msg_1)

    user = User(
        name=_require_text(user_data, "name"),
        link=source_url,
        games=[_parse_game(game) for game in games_data],
    )
    return CachedUser(user=user, fetched_at=fetched_at)


def load_user_cache(source_url: str) -> CachedUser | None:
    """Load a cache only when it belongs to the currently configured URL."""
    try:
        contents = _CACHE_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        msg = "Der lokale Spiel-Cache konnte nicht gelesen werden."
        raise UserCacheError(msg) from exc

    try:
        payload = _require_object(json.loads(contents), "Cache")
        return _parse_cached_user(payload, source_url)
    except (TypeError, ValueError) as exc:
        msg_0 = "Der lokale Spiel-Cache ist beschädigt oder ungültig."
        raise UserCacheError(msg_0) from exc
