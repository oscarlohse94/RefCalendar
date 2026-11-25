from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from app_paths import PROJECT_ROOT, get_application_directory


class ApplicationDirectoryTests(unittest.TestCase):
    def test_uses_source_checkout_directory_when_not_frozen(self) -> None:
        with patch.object(sys, "frozen", False, create=True):
            self.assertEqual(get_application_directory(), PROJECT_ROOT)

    def test_uses_executable_directory_when_frozen(self) -> None:
        executable = Path("C:/Program Files/RefCalendar/RefCalendar.exe")
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", str(executable)),
        ):
            self.assertEqual(get_application_directory(), executable.parent)


if __name__ == "__main__":
    unittest.main()
