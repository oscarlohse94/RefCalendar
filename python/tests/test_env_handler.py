# Copyright (c) 2026 Oscar Lohse

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values
from keyring.errors import KeyringError

from env_handler import (
    get_dhb_url,
    load_environment,
    set_dhb_url,
    set_referee_name,
)


class EnvironmentHandlerTests(unittest.TestCase):
    @patch("env_handler.keyring.set_password")
    def test_set_dhb_url_saves_only_to_credential_store(self, set_password) -> None:
        dhb_url = "https://dhb.refsoft.de/api/index.php?m=private-link"
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "config.env"
            env_file.write_text("REFEREE_NAME=Alex Example\n", encoding="utf-8")

            with (
                patch("env_handler._ENV_FILE", env_file),
                patch.dict(os.environ, {"DHB_URL": "stale"}, clear=False),
            ):
                set_dhb_url(f"  {dhb_url}  ")

                values = dotenv_values(env_file)
                self.assertEqual(values["REFEREE_NAME"], "Alex Example")
                self.assertNotIn("DHB_URL", values)
                self.assertNotIn("DHB_URL", os.environ)
                set_password.assert_called_once_with("RefCalendar", "DHB_URL", dhb_url)

    def test_set_dhb_url_rejects_invalid_url_without_creating_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            with patch("env_handler._ENV_FILE", env_file):
                with self.assertRaises(ValueError):
                    set_dhb_url("https://example.com")

            self.assertFalse(env_file.exists())

    @patch("env_handler.keyring.get_password")
    def test_get_dhb_url_reads_credential_store(self, get_password) -> None:
        dhb_url = "https://dhb.refsoft.de/api/index.php?m=stored-link"
        get_password.return_value = dhb_url

        self.assertEqual(get_dhb_url(), dhb_url)
        get_password.assert_called_once_with("RefCalendar", "DHB_URL")

    @patch("env_handler.keyring.set_password")
    @patch("env_handler.keyring.get_password", return_value=None)
    def test_load_migrates_plaintext_link_out_of_config(
        self,
        get_password,
        set_password,
    ) -> None:
        dhb_url = "https://dhb.refsoft.de/api/index.php?m=legacy-link"
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "config.env"
            env_file.write_text(
                f"REFEREE_NAME=Alex Example\nDHB_URL={dhb_url}\n",
                encoding="utf-8",
            )

            with (
                patch("env_handler._ENV_FILE", env_file),
                patch.dict(os.environ, {}, clear=True),
            ):
                load_environment()

                values = dotenv_values(env_file)
                self.assertNotIn("DHB_URL", values)
                self.assertEqual(os.environ["REFEREE_NAME"], "Alex Example")
                self.assertNotIn("DHB_URL", os.environ)

            get_password.assert_called_once_with("RefCalendar", "DHB_URL")
            set_password.assert_called_once_with("RefCalendar", "DHB_URL", dhb_url)

    @patch("env_handler.keyring.set_password")
    @patch("env_handler.keyring.get_password")
    def test_load_keeps_existing_credential_store_value(
        self,
        get_password,
        set_password,
    ) -> None:
        old_url = "https://dhb.refsoft.de/api/index.php?m=legacy-link"
        stored_url = "https://dhb.refsoft.de/api/index.php?m=stored-link"
        get_password.return_value = stored_url
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "config.env"
            env_file.write_text(f"DHB_URL={old_url}\n", encoding="utf-8")

            with patch("env_handler._ENV_FILE", env_file):
                load_environment()

            self.assertNotIn("DHB_URL", dotenv_values(env_file))
            get_password.assert_called_once_with("RefCalendar", "DHB_URL")
            set_password.assert_not_called()

    @patch("env_handler.keyring.set_password")
    def test_load_does_not_remove_link_if_credential_store_fails(
        self,
        set_password,
    ) -> None:
        dhb_url = "https://dhb.refsoft.de/api/index.php?m=legacy-link"
        set_password.side_effect = KeyringError("credential store unavailable")
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "config.env"
            env_file.write_text(f"DHB_URL={dhb_url}\n", encoding="utf-8")

            with (
                patch("env_handler._ENV_FILE", env_file),
                patch("env_handler.keyring.get_password", return_value=None),
            ):
                with self.assertRaisesRegex(RuntimeError, "Anmeldeinformationsspeicher"):
                    load_environment()

            self.assertEqual(dotenv_values(env_file)["DHB_URL"], dhb_url)

    def test_set_referee_name_preserves_other_settings_and_updates_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "config.env"
            env_file.write_text("APP_THEME=system\n", encoding="utf-8")

            with (
                patch("env_handler._ENV_FILE", env_file),
                patch.dict(os.environ, {}, clear=False),
            ):
                set_referee_name("  Alex Example  ")

                values = dotenv_values(env_file)
                self.assertEqual(values["APP_THEME"], "system")
                self.assertNotIn("DHB_URL", values)
                self.assertEqual(values["REFEREE_NAME"], "Alex Example")
                self.assertEqual(os.environ["REFEREE_NAME"], "Alex Example")

    def test_set_referee_name_rejects_empty_name(self) -> None:
        with self.assertRaises(ValueError):
            set_referee_name("  ")


if __name__ == "__main__":
    unittest.main()
