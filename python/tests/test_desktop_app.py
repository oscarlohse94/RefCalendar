# Copyright (c) 2026 Oscar Lohse

from queue import Queue
import unittest
from unittest.mock import Mock, patch

from desktop_app import RefCalendarWindow
from game_data import Game, User


class DesktopAppTests(unittest.TestCase):
    def test_sync_requires_a_connected_google_account(self) -> None:
        window = RefCalendarWindow.__new__(RefCalendarWindow)
        window.root = Mock()
        window._google_connected = False

        with (
            patch("desktop_app.messagebox.showwarning") as showwarning,
            patch("desktop_app.get_dhb_url") as get_dhb_url,
        ):
            window._sync_with_google()

        showwarning.assert_called_once_with(
            "Google-Konto nicht verknüpft",
            "Verknüpfe zuerst dein Google-Konto.",
            parent=window.root,
        )
        get_dhb_url.assert_not_called()

    def test_displays_game_fields_in_the_games_table(self) -> None:
        window = RefCalendarWindow.__new__(RefCalendarWindow)
        window.games_tree = Mock()
        window.games_tree.get_children.return_value = []
        window.games_status = Mock()
        game = Game(
            game_id=424242,
            league="Testliga",
            date="17.11.2026",
            time="18:30",
            home_team="Heimteam",
            away_team="Gastteam",
            location="Sporthalle\nBeispielstraße 1",
            referee=(None, None, None),
        )

        window._display_games([game])

        window.games_tree.insert.assert_called_once_with(
            "",
            "end",
            iid="424242",
            values=(
                "17.11.2026",
                "18:30",
                "Testliga",
                "Heimteam",
                "Gastteam",
                "Sporthalle, Beispielstraße 1",
            ),
        )
        window.games_status.set.assert_called_once_with("1 Spiele geladen")

    def test_sync_worker_fetches_current_games_and_returns_sync_counts(self) -> None:
        window = RefCalendarWindow.__new__(RefCalendarWindow)
        window._sync_results = Queue()
        source_url = "https://dhb.refsoft.de/api/index.php?m=private-link"
        user = User(name="Alex Example", link=source_url)

        with (
            patch("desktop_app.fetch_html", return_value="<html></html>"),
            patch("desktop_app.parse_user", return_value=user),
            patch("desktop_app.save_user_cache") as save_cache,
            patch("desktop_app.persist_referee_name") as save_name,
            patch("desktop_app.games_to_google_calendar_events", return_value=[]) as convert,
            patch("desktop_app.sync_google_calendar_events", return_value=(2, 3)) as sync,
        ):
            window._sync_worker(source_url)

        result = window._sync_results.get_nowait()

        self.assertEqual(result.user, user)
        self.assertEqual((result.created, result.updated), (2, 3))
        save_cache.assert_called_once_with(user, source_url)
        save_name.assert_called_once_with(user.name)
        convert.assert_called_once_with(user.games)
        sync.assert_called_once_with([], allow_authorization=False)


if __name__ == "__main__":
    unittest.main()
