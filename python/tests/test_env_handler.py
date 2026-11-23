# Copyright (c) 2026 Oscar Lohse

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from env_handler import set_dhb_url, set_referee_name


class EnvironmentHandlerTests(unittest.TestCase):
    def test_set_dhb_url_preserves_other_settings_and_updates_environment(self) -> None:
        dhb_url = "https://dhb.refsoft.de/api/index.php?m=private-link"
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "config.env"
            env_file.write_text("REFEREE_NAME=Alex Example\n", encoding="utf-8")

            with (
                patch("env_handler._ENV_FILE", env_file),
                patch.dict(os.environ, {}, clear=False),
            ):
                set_dhb_url(f"  {dhb_url}  ")

                values = dotenv_values(env_file)
                self.assertEqual(values["REFEREE_NAME"], "Alex Example")
                self.assertEqual(values["DHB_URL"], dhb_url)
                self.assertEqual(os.environ["DHB_URL"], dhb_url)

    def test_set_dhb_url_rejects_invalid_url_without_creating_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            with patch("env_handler._ENV_FILE", env_file):
                with self.assertRaises(ValueError):
                    set_dhb_url("https://example.com")

            self.assertFalse(env_file.exists())

    def test_set_referee_name_preserves_other_settings_and_updates_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "config.env"
            env_file.write_text("DHB_URL=https://dhb.refsoft.de/api/index.php?m=existing\n", encoding="utf-8")

            with (
                patch("env_handler._ENV_FILE", env_file),
                patch.dict(os.environ, {}, clear=False),
            ):
                set_referee_name("  Alex Example  ")

                values = dotenv_values(env_file)
                self.assertEqual(values["DHB_URL"], "https://dhb.refsoft.de/api/index.php?m=existing")
                self.assertEqual(values["REFEREE_NAME"], "Alex Example")
                self.assertEqual(os.environ["REFEREE_NAME"], "Alex Example")

    def test_set_referee_name_rejects_empty_name(self) -> None:
        with self.assertRaises(ValueError):
            set_referee_name("  ")


if __name__ == "__main__":
    unittest.main()
