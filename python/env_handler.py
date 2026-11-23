# Copyright (c) 2026 Oscar Lohse

"""For Handling the environment variables related to the DHB RefSoft URL."""

import os

import keyring
from app_paths import CONFIG_FILE
from dotenv import dotenv_values, load_dotenv, set_key, unset_key
from keyring.errors import KeyringError

_ENV_FILE = CONFIG_FILE
_DHB_URL_PREFIX = "https://dhb.refsoft.de/api/index.php?m="
_KEYRING_SERVICE = "RefCalendar"
_DHB_URL_KEY = "DHB_URL"

if os.name == "nt":
    from keyring.backends.Windows import WinVaultKeyring

    keyring.set_keyring(WinVaultKeyring())


def _prepare_config_file() -> None:
    try:
        _ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        msg = "Der RefCalendar-Benutzerordner konnte nicht vorbereitet werden."
        raise OSError(msg) from exc


def load_environment() -> None:
    """Load the per-user RefCalendar configuration."""
    _prepare_config_file()
    _migrate_plaintext_dhb_url()
    os.environ.pop(_DHB_URL_KEY, None)
    load_dotenv(_ENV_FILE)


def validate_dhb_url(dhb_url: str) -> str:
    """Return a normalized DHB URL or raise ValueError if it is invalid."""
    value = dhb_url.strip()
    if not value.startswith(_DHB_URL_PREFIX) or len(value) == len(_DHB_URL_PREFIX):
        msg = f"RefSoft-URL ist ungültig. Sie muss mit '{_DHB_URL_PREFIX}' beginnen und einen Wert enthalten."
        raise ValueError(msg)
    return value


def _set_environment_value(key: str, value: str) -> None:
    _prepare_config_file()
    saved, _, _ = set_key(
        str(_ENV_FILE),
        key,
        value,
        quote_mode="always",
    )
    if not saved:
        msg = "Die Benutzerkonfiguration konnte nicht aktualisiert werden."
        raise OSError(msg)
    os.environ[key] = value


def _migrate_plaintext_dhb_url() -> None:
    config = dotenv_values(_ENV_FILE)
    plaintext_url = config.get(_DHB_URL_KEY)
    if not plaintext_url:
        return

    dhb_url = validate_dhb_url(plaintext_url)
    try:
        stored_url = keyring.get_password(_KEYRING_SERVICE, _DHB_URL_KEY)
        if stored_url is None:
            keyring.set_password(_KEYRING_SERVICE, _DHB_URL_KEY, dhb_url)
    except KeyringError as exc:
        msg = "Der DHB-Link konnte nicht in den Anmeldeinformationsspeicher übertragen werden."
        raise RuntimeError(msg) from exc

    removed, _ = unset_key(_ENV_FILE, _DHB_URL_KEY)
    if not removed:
        msg = "Der DHB-Link wurde geschützt gespeichert, konnte aber nicht aus der Benutzerkonfiguration entfernt werden."
        raise OSError(msg)


def get_dhb_url() -> str:
    """Retrieve the DHB RefSoft URL from the system credential store."""
    try:
        dhb_url = keyring.get_password(_KEYRING_SERVICE, _DHB_URL_KEY)
    except KeyringError as exc:
        msg = "Der DHB-Link konnte nicht aus dem Windows-Anmeldeinformationsspeicher gelesen werden."
        raise RuntimeError(msg) from exc
    if not dhb_url or not dhb_url.strip():
        msg = "RefSoft-URL fehlt. Trage deinen persönlichen Link in RefCalendar ein."
        raise RuntimeError(msg)
    try:
        return validate_dhb_url(dhb_url)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc


def set_dhb_url(new_url: str) -> None:
    """Validate and persist the DHB RefSoft URL in the system credential store."""
    dhb_url = validate_dhb_url(new_url)
    try:
        keyring.set_password(_KEYRING_SERVICE, _DHB_URL_KEY, dhb_url)
    except KeyringError as exc:
        msg = "Der DHB-Link konnte nicht im Windows-Anmeldeinformationsspeicher gespeichert werden."
        raise OSError(msg) from exc
    os.environ.pop(_DHB_URL_KEY, None)


def get_referee_name() -> str:
    """Retrieve the referee name from the environment variables."""
    return os.getenv("REFEREE_NAME", "").strip()


def set_referee_name(new_name: str) -> None:
    """Validate and persist the referee name."""
    name = new_name.strip()
    if not name:
        msg = "Der Schiedsrichtername darf nicht leer sein."
        raise ValueError(msg)
    _set_environment_value("REFEREE_NAME", name)
