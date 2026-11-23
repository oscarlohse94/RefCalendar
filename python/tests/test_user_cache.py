# Copyright (c) 2026 Oscar Lohse

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from game_data import Game, Referee, User
from user_cache import UserCacheError, load_user_cache, save_user_cache


class UserCacheTests(unittest.TestCase):
    def test_round_trips_user_games_without_storing_source_url(self) -> None:
        source_url = "https://dhb.refsoft.de/api/index.php?m=private-token"
        user = User(
            name="Alex Example",
            link=source_url,
            games=[
                Game(
                    game_id=424242,
                    league="Testliga",
                    date="17.11.2026",
                    time="18:30",
                    home_team="Heimteam",
                    away_team="Gastteam",
                    location="Sporthalle\nBeispielstraße 1",
                    referee=(
                        Referee(role="SR1", name="Alex Example", phone="+49 111"),
                        Referee(role="SR2", name="Sam Example"),
                        None,
                    ),
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_file = Path(temporary_directory) / "user-cache.json"
            with patch("user_cache._CACHE_FILE", cache_file):
                save_user_cache(user, source_url)
                cached_user = load_user_cache(source_url)
                contents = cache_file.read_text(encoding="utf-8")

            self.assertNotIn(source_url, contents)
            self.assertIsNotNone(cached_user)
            self.assertEqual(cached_user.user.name, user.name)
            self.assertEqual(cached_user.user.link, source_url)
            self.assertEqual(cached_user.user.games, user.games)
            self.assertIsNotNone(cached_user.fetched_at.tzinfo)

    def test_does_not_load_cache_for_another_source_url(self) -> None:
        source_url = "https://dhb.refsoft.de/api/index.php?m=first"
        user = User(name="Alex Example", link=source_url)

        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_file = Path(temporary_directory) / "user-cache.json"
            with patch("user_cache._CACHE_FILE", cache_file):
                save_user_cache(user, source_url)

                self.assertIsNone(
                    load_user_cache(
                        "https://dhb.refsoft.de/api/index.php?m=second"
                    )
                )

    def test_rejects_malformed_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_file = Path(temporary_directory) / "user-cache.json"
            cache_file.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")

            with patch("user_cache._CACHE_FILE", cache_file):
                with self.assertRaises(UserCacheError):
                    load_user_cache("https://dhb.refsoft.de/api/index.php?m=source")


if __name__ == "__main__":
    unittest.main()
