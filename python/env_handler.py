"""For Handling the environment variables related to the DHB RefSoft URL."""

import os

from dotenv import load_dotenv


def load_environment() -> None:
    """Load variables from the project's local .env file."""
    load_dotenv()


def get_dhb_url() -> str:
    """Retrieve the DHB RefSoft URL from the environment variables."""
    dhb_url = os.getenv("DHB_URL", "").strip()
    if not dhb_url:
        msg = "RefSoft-URL fehlt. Lege eine lokale .env-Datei an und trage dort deinen persönlichen Link ein."
        raise RuntimeError(msg)
    if not dhb_url.startswith("https://dhb.refsoft.de/api/index.php?m="):
        msg = "RefSoft-URL ist ungültig. Sie beginnt immer mit 'https://dhb.refsoft.de/api/index.php?m=' beginnen."
        raise RuntimeError(msg)
    return dhb_url