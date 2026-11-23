# Copyright (c) 2026 Oscar Lohse

import unittest

from game_data import Game, Referee
from game_to_json import (
    game_to_google_calendar_event,
    games_to_google_calendar_events,
)


def _game(
    *,
    league: str = "H-BL1-H",
    date: str = "17.11.2026",
    time: str = "18:30",
    referee: tuple[Referee | None, Referee | None, Referee | None] | None = None,
) -> Game:
    if referee is None:
        referee = (
            Referee(
                role="SR1",
                name="Alex Example",
                phone="040-123",
                mobile="0170-123",
                mail="sr1@example.test",
            ),
            Referee(role="SR2", name="Sam Example"),
            None,
        )
    return Game(
        game_id=424242,
        league=league,
        date=date,
        time=time,
        home_team="Heimteam",
        away_team="Gastteam",
        location="Sporthalle\nBeispielstraße 1",
        referee=referee,
    )


class GameToJsonTests(unittest.TestCase):
    def test_builds_google_calendar_event(self) -> None:
        event = game_to_google_calendar_event(_game())

        self.assertRegex(event["id"], r"^[a-v0-9]{5,1024}$")
        self.assertEqual(event["summary"], "1. BLH: Heimteam - Gastteam")
        self.assertEqual(event["location"], "Sporthalle\nBeispielstraße 1")
        self.assertEqual(
            event["description"],
            "Spielnummer: 424242\n"
            "SR1: Alex Example, Telefon: 040-123, Mobil: 0170-123, "
            "Mail: sr1@example.test\n"
            "SR2: Sam Example",
        )
        self.assertEqual(
            event["start"],
            {
                "dateTime": "2026-11-17T18:30:00+01:00",
                "timeZone": "Europe/Berlin",
            },
        )
        self.assertEqual(
            event["end"],
            {
                "dateTime": "2026-11-17T20:30:00+01:00",
                "timeZone": "Europe/Berlin",
            },
        )

    def test_formats_women_league_and_omits_missing_referees(self) -> None:
        event = game_to_google_calendar_event(
            _game(league="H-BL1-D", referee=(None, None, None))
        )

        self.assertEqual(event["summary"], "1. BLD: Heimteam - Gastteam")
        self.assertEqual(event["description"], "Spielnummer: 424242")

    def test_formats_field_bundesliga(self) -> None:
        event = game_to_google_calendar_event(_game(league="F-BL2-D"))

        self.assertEqual(event["summary"], "2. BLD: Heimteam - Gastteam")

    def test_formats_oberliga(self) -> None:
        event = game_to_google_calendar_event(_game(league="H-BER-OL-D"))

        self.assertEqual(event["summary"], "OLD: Heimteam - Gastteam")

    def test_formats_regionalliga_with_region(self) -> None:
        expected_labels = {
            "H-BER-RLN-H": "RLH",
            "H-BER-RLO-H": "RLH",
            "H-BER-RLS-H": "RLH",
            "H-BER-RLW-H": "RLH",
            "F-BER-RLN-D": "RLD",
            "H-BER-RL-H": "RLH",
        }

        for league, label in expected_labels.items():
            with self.subTest(league=league):
                event = game_to_google_calendar_event(_game(league=league))

                self.assertEqual(event["summary"], f"{label}: Heimteam - Gastteam")

    def test_keeps_unknown_league_code(self) -> None:
        event = game_to_google_calendar_event(_game(league="H-UNKNOWN-H"))

        self.assertEqual(event["summary"], "H-UNKNOWN-H: Heimteam - Gastteam")

    def test_two_hour_duration_is_correct_across_dst_transition(self) -> None:
        event = game_to_google_calendar_event(_game(date="25.10.2026", time="01:30"))

        self.assertEqual(event["start"]["dateTime"], "2026-10-25T01:30:00+02:00")
        self.assertEqual(event["end"]["dateTime"], "2026-10-25T02:30:00+01:00")

    def test_rejects_invalid_date_or_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "Spiel 424242"):
            game_to_google_calendar_event(_game(date="invalid"))

    def test_converts_games_to_a_list_of_calendar_event_dicts(self) -> None:
        events = games_to_google_calendar_events(
            [_game(), _game(league="F-BL2-D")]
        )

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["summary"], "1. BLH: Heimteam - Gastteam")
        self.assertEqual(events[1]["summary"], "2. BLD: Heimteam - Gastteam")
        self.assertIsInstance(events[0], dict)


if __name__ == "__main__":
    unittest.main()
