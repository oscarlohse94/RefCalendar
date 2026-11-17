"""Fetch the personal DHB page as HTML."""

from __future__ import annotations

from urllib.parse import urlsplit

import requests


class GameFetchError(RuntimeError):
    """Raised when the DHB page cannot be retrieved safely."""


def fetch_html(url: str, timeout: tuple[int, int] = (10, 30)) -> str:
    """Fetch the DHB page using its personal URL.

    The URL is intentionally never logged or included in our error messages,
    because it contains a personal access token.
    """
    parsed_url = urlsplit(url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        msg = "DHB_URL muss eine gültige HTTPS-Adresse sein."
        raise GameFetchError(msg)

    headers = {
        "User-Agent": "RefCalendar/0.1 (+personal referee calendar synchronizer)",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        with requests.Session() as session:
            response = session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or response.encoding
            html = response.text
    except requests.RequestException as exc:
        # Do not include the exception text: requests may include the secret URL.
        msg = f"DHB-Seite konnte nicht abgerufen werden ({type(exc).__name__})."
        raise GameFetchError(msg) from None

    if not html.strip():
        msg = "Der DHB-Server hat eine leere Antwort geliefert."
        raise GameFetchError(msg)
    return html
