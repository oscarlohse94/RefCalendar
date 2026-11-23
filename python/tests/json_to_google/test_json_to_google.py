# Copyright (c) 2026 Oscar Lohse

import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from googleapiclient.errors import HttpError

from game_data import Game
from game_to_json import games_to_google_calendar_events
import main
from json_to_google import (
    GoogleCalendarSyncError,
    _run_oauth_flow,
    _upsert_events,
    test_google_calendar_access,
)


def _event():
    game = Game(
        game_id=424242,
        league="H-BL1-H",
        date="17.11.2026",
        time="18:30",
        home_team="Heimteam",
        away_team="Gastteam",
        location="Sporthalle",
        referee=(None, None, None),
    )
    return games_to_google_calendar_events([game])[0]


def _http_error(status: int) -> HttpError:
    response = SimpleNamespace(status=status, reason="Test response")
    return HttpError(response, b'{"error": {"message": "test"}}')


class _FakeRequest:
    def __init__(self, result=None, error: HttpError | None = None) -> None:
        self._result = result
        self._error = error

    def execute(self):
        if self._error is not None:
            raise self._error
        return self._result


class _FakeEvents:
    def __init__(
        self,
        existing_ids: set[str] | None = None,
        insert_error: HttpError | None = None,
    ) -> None:
        self.existing_ids = existing_ids or set()
        self.insert_error = insert_error
        self.inserted = []
        self.patched = []
        self.list_parameters = None

    def get(self, *, calendarId: str, eventId: str) -> _FakeRequest:
        if eventId in self.existing_ids:
            return _FakeRequest({"id": eventId})
        return _FakeRequest(error=_http_error(404))

    def insert(self, *, calendarId: str, body: dict) -> _FakeRequest:
        if self.insert_error is not None:
            return _FakeRequest(error=self.insert_error)
        self.inserted.append(body)
        self.existing_ids.add(body["id"])
        return _FakeRequest(body)

    def patch(
        self,
        *,
        calendarId: str,
        eventId: str,
        body: dict,
    ) -> _FakeRequest:
        self.patched.append((eventId, body))
        return _FakeRequest(body)

    def list(self, **parameters) -> _FakeRequest:
        self.list_parameters = parameters
        return _FakeRequest({"items": [{"id": "test-event"}]})


class _FakeService:
    def __init__(self, events: _FakeEvents) -> None:
        self._events = events

    def events(self) -> _FakeEvents:
        return self._events


class GoogleCalendarSyncTests(unittest.TestCase):
    def test_oauth_flow_does_not_open_browser_or_log_callback_code(self) -> None:
        class FakeFlow:
            options = None

            def run_local_server(self, *, port: int, open_browser: bool) -> str:
                self.options = (port, open_browser)
                logging.getLogger("google_auth_oauthlib.flow").info(
                    "GET /?code=example-one-time-code HTTP/1.1"
                )
                return "credentials"

        flow = FakeFlow()
        logger = logging.getLogger("google_auth_oauthlib.flow")
        previous_level = logger.level

        with self.assertNoLogs("google_auth_oauthlib.flow", level="INFO"):
            result = _run_oauth_flow(flow)

        self.assertEqual(result, "credentials")
        self.assertEqual(flow.options, (0, False))
        self.assertEqual(logger.level, previous_level)

    def test_oauth_flow_can_open_browser_for_desktop_app(self) -> None:
        class FakeFlow:
            options = None

            def run_local_server(self, *, port: int, open_browser: bool) -> str:
                self.options = (port, open_browser)
                return "credentials"

        flow = FakeFlow()

        result = _run_oauth_flow(flow, open_browser=True)

        self.assertEqual(result, "credentials")
        self.assertEqual(flow.options, (0, True))

    @patch("json_to_google._build_calendar_service")
    def test_calendar_access_check_reads_only_one_event_id(
        self,
        build_service,
    ) -> None:
        api = _FakeEvents()
        build_service.return_value = _FakeService(api)

        test_google_calendar_access()

        self.assertEqual(
            api.list_parameters,
            {
                "calendarId": "primary",
                "maxResults": 1,
                "fields": "items(id)",
            },
        )
        self.assertEqual(api.inserted, [])
        self.assertEqual(api.patched, [])

    @patch("main.get_dhb_url")
    @patch("main.load_environment")
    @patch("main.test_google_calendar_access")
    def test_main_auth_test_skips_dhb_fetch(
        self,
        test_access,
        load_environment,
        get_dhb_url,
    ) -> None:
        with patch("sys.argv", ["main.py", "--test-google-login"]):
            result = main.main()

        self.assertEqual(result, 0)
        test_access.assert_called_once_with()
        load_environment.assert_not_called()
        get_dhb_url.assert_not_called()

    def test_inserts_event_when_it_does_not_exist(self) -> None:
        event = _event()
        api = _FakeEvents()

        created, updated = _upsert_events(_FakeService(api), [event])

        self.assertEqual((created, updated), (1, 0))
        self.assertEqual(api.inserted, [event])
        self.assertEqual(api.patched, [])

    def test_updates_existing_event(self) -> None:
        event = _event()
        api = _FakeEvents(existing_ids={event["id"]})

        created, updated = _upsert_events(_FakeService(api), [event])

        self.assertEqual((created, updated), (0, 1))
        self.assertEqual(api.inserted, [])
        self.assertEqual(api.patched, [(event["id"], {
            key: value for key, value in event.items() if key != "id"
        })])

    def test_updates_after_insert_conflict_race(self) -> None:
        event = _event()
        api = _FakeEvents(insert_error=_http_error(409))

        created, updated = _upsert_events(_FakeService(api), [event])

        self.assertEqual((created, updated), (0, 1))
        self.assertEqual(len(api.patched), 1)

    def test_reports_unexpected_google_api_errors(self) -> None:
        event = _event()
        api = _FakeEvents()

        def fail_lookup(*, calendarId: str, eventId: str) -> _FakeRequest:
            return _FakeRequest(error=_http_error(403))

        api.get = fail_lookup
        with self.assertRaisesRegex(GoogleCalendarSyncError, "HTTP 403"):
            _upsert_events(_FakeService(api), [event])


if __name__ == "__main__":
    unittest.main()
