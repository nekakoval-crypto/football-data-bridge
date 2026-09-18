import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from stage80_match_event_capture import (
    candidate_fixtures,
    merge_rows,
    normalize_events,
    sync_backlog,
)


class Stage80MatchEventCaptureTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
        self.fixture = {
            "fixture_id": "100",
            "provider_league_id": "140",
            "league_name": "La Liga",
            "season": "2026",
            "round": "Round 7",
            "kickoff_utc": "2026-09-18T10:00:00Z",
            "home_team": "Home",
            "away_team": "Away",
            "source_status": "FT",
            "status": "FINISHED",
        }

    def test_normalizes_and_deduplicates_event_identity(self):
        payload = {
            "response": [
                {
                    "time": {"elapsed": 10, "extra": None},
                    "team": {"id": 1, "name": "Home"},
                    "player": {"id": 11, "name": "P1"},
                    "assist": {"id": None, "name": None},
                    "type": "Goal",
                    "detail": "Normal Goal",
                    "comments": None,
                },
                {
                    "time": {"elapsed": 10, "extra": None},
                    "team": {"id": 1, "name": "Home"},
                    "player": {"id": 11, "name": "P1"},
                    "assist": {"id": None, "name": None},
                    "type": "Goal",
                    "detail": "Normal Goal",
                    "comments": None,
                },
            ]
        }
        rows = normalize_events(payload, self.fixture, "2026-09-18T12:00:00Z")
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["event_id"], rows[1]["event_id"])
        rerun = normalize_events(payload, self.fixture, "2026-09-18T13:00:00Z")
        merged = merge_rows(rows, rerun)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["observed_at_utc"], "2026-09-18T12:00:00Z")

    def test_terminal_fixture_enters_backlog_and_captured_after_events(self):
        before = sync_backlog([], [self.fixture], [], self.now)
        self.assertEqual(before["pending"], 1)
        self.assertEqual(before["new_rows"], 1)
        event = {
            "event_id": "e1",
            "fixture_id": "100",
            "observed_at_utc": "2026-09-18T12:00:00Z",
        }
        after = sync_backlog(before["rows"], [], [event], self.now)
        self.assertEqual(after["captured"], 1)
        self.assertEqual(after["pending"], 0)

    def test_fair_retry_prioritizes_never_attempted(self):
        rows = [
            {
                **self.fixture,
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "2026-09-18T11:00:00Z",
            },
            {
                **self.fixture,
                "fixture_id": "101",
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "",
            },
        ]
        out = candidate_fixtures(rows, set(), self.now, 2)
        self.assertEqual([r["fixture_id"] for r in out], ["101", "100"])

    def test_empty_provider_response_stays_retryable(self):
        rows = normalize_events({"response": []}, self.fixture, "2026-09-18T12:00:00Z")
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
