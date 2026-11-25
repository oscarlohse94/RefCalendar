# Copyright (c) 2026 Oscar Lohse

"""Resolve per-user RefCalendar storage paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_application_directory() -> Path:
    """Return the directory containing the app executable or source checkout."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


APPLICATION_DIRECTORY = get_application_directory()


def _config_directory() -> Path:
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base_directory = (
            Path(local_app_data)
            if local_app_data
            else Path.home() / "AppData" / "Local"
        )
        return base_directory / "RefCalendar"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "RefCalendar"
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "refcalendar"


CONFIG_DIRECTORY = _config_directory()
CONFIG_FILE = CONFIG_DIRECTORY / "config.env"
TOKEN_FILE = CONFIG_DIRECTORY / "token.json"
