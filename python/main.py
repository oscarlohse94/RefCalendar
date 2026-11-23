# Copyright (c) 2026 Oscar Lohse

"""RefCalendar prototype: fetch DHB games and export them as JSON."""

from __future__ import annotations

import argparse
import json
import logging

from env_handler import get_dhb_url, load_environment
from game_to_json import games_to_google_calendar_events
from get_games import fetch_html
from html_to_data import parse_games
from json_to_google import (
    sync_google_calendar_events,
    test_google_calendar_access,
)

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DHB-Spielansetzungen auslesen und als Kalendertermine vorbereiten.")
    google_actions = parser.add_mutually_exclusive_group()
    google_actions.add_argument(
        "--test-google-login",
        action="store_true",
        help="Google-OAuth und Lesezugriff testen, ohne Kalenderdaten zu ändern.",
    )
    google_actions.add_argument(
        "--sync-calendar",
        action="store_true",
        help="Events im primären Google Calendar erstellen oder aktualisieren.",
    )
    return parser


def main() -> int:
    """Global entry point for the RefCalendar prototype."""
    args = _build_parser().parse_args()

    try:
        if args.test_google_login:
            test_google_calendar_access()
            logger.info("Google-OAuth und Lesezugriff auf den primären Kalender sind erfolgreich.")
            return 0

        load_environment()
        dhb_url = get_dhb_url()
        html = fetch_html(dhb_url)
        games = parse_games(html)
        logger.info("DHB-Seite wurde erfolgreich abgerufen und verarbeitet.")
        calendar_events = games_to_google_calendar_events(games)
        if args.sync_calendar:
            created, updated = sync_google_calendar_events(calendar_events)
            logger.info(
                "Google Calendar synchronisiert: %d erstellt, %d aktualisiert.",
                created,
                updated,
            )
        else:
            print(json.dumps(calendar_events, ensure_ascii=False, indent=2))  # noqa: T201

    except (OSError, RuntimeError, ValueError):
        logger.exception("Abbruch")
        return 1
    else:
        return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
