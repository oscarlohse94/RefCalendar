"""RefCalendar prototype: fetch DHB games and export them as JSON."""

from __future__ import annotations

import logging

from env_handler import get_dhb_url, load_environment
from get_games import fetch_html
from html_to_data import parse_games

logger = logging.getLogger(__name__)

def main() -> int:
    """Global entry point for the RefCalendar prototype."""
    load_environment()

    try:
        dhb_url = get_dhb_url()
        html = fetch_html(dhb_url)
        games = parse_games(html)
        logger.info("DHB-Seite wurde erfolgreich abgerufen und verarbeitet.")
        for game in games:
            logger.info("Verarbeitetes Spiel: %s", game)

    except (OSError, RuntimeError, ValueError):
        logger.exception("Abbruch")
        return 1
    else:
        return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
