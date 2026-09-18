from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage71_observation_audit as audit
import stage81_team_match_statistics_capture as s81


NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def fixture(fid="100", kickoff="2026-09-17T09:00:00Z"):
    return {
        "fixture_id": fid,
        "provider_league_id": "39",
        "league_name": "Premier League",
        "season": "2026",
        "round": "Regular Season - 4",
        "kickoff_utc": kickoff,
        "home_team": "Home FC",
        "away_team": "Away FC",
        "source_status": "FT",
        "status": "FINISHED",
    }


def complete_payload():
    return {
        "response": [
            {
                "team": {"id": 10, "name": "Home FC"},
                "statistics": [
                    {"type": "Shots on Goal", "value": 6},
                    {"type": "Shots off Goal", "value": 4},
                    {"type": "Total Shots", "value": 14},
                    {"type": "Blocked Shots", "value": 4},
                    {"type": "Shots insidebox", "value": 9},
                    {"type": "Shots outsidebox", "value": 5},
                    {"type": "Fouls", "value": 11},
                    {"type": "Corner Kicks", "value": 7},
                    {"type": "Offsides", "value": 2},
                    {"type": "Ball Possession", "value": "61%"},
                    {"type": "Yellow Cards", "value": 2},
                    {"type": "Red Cards", "value": None},
                    {"type": "Goalkeeper Saves", "value": 3},
                    {"type": "Total passes", "value": 540},
                    {"type": "Passes accurate", "value": 472},
                    {"type": "Passes %", "value": "87%"},
                    {"type": "expected_goals", "value": "1.84"},
                ],
            },
            {
                "team": {"id": 20, "name": "Away FC"},
                "statistics": [
                    {"type": "Shots on Goal", "value": 4},
                    {"type": "Total Shots", "value": 9},
                    {"type": "Corner Kicks", "value": 3},
                    {"type": "Ball Possession", "value": "39%"},
                    {"type": "Total passes", "value": 331},
                    {"type": "Passes accurate", "value": 250},
                    {"type": "Passes %", "value": "76%"},
                    {"type": "expected_goals", "value": "0.92"},
                ],
            },
        ]
    }


class Stage81Tests(unittest.TestCase):

    def test_terminal_fixture_is_queued(self):
        result = s81.sync_backlog([], [fixture()], [], NOW)

        self.assertEqual(result["new_rows"], 1)
        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["captured"], 0)

        row = result["rows"][0]
        self.assertEqual(row["fixture_id"], "100")
        self.assertEqual(row["backlog_status"], "PENDING")
        self.assertEqual(
            row["queue_source"],
            "current_round_terminal_fixture",
        )

    def test_backlog_survives_round_rotation(self):
        first = s81.sync_backlog([], [fixture()], [], NOW)

        later = s81.sync_backlog(
            first["rows"],
            [],
            [],
            datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(len(later["rows"]), 1)
        self.assertEqual(later["pending"], 1)
        self.assertEqual(
            later["rows"][0]["first_queued_at_utc"],
            first["rows"][0]["first_queued_at_utc"],
        )

    def test_normalize_complete_home_and_away(self):
        rows = s81.normalize_team_statistics(
            complete_payload(),
            fixture(),
            "2026-09-17T12:00:00Z",
        )

        self.assertEqual(len(rows), 2)

        by_side = {row["side"]: row for row in rows}

        self.assertEqual(set(by_side), {"HOME", "AWAY"})
        self.assertEqual(by_side["HOME"]["team_id"], "10")
        self.assertEqual(by_side["AWAY"]["team_id"], "20")

        self.assertEqual(by_side["HOME"]["shots_total"], 14)
        self.assertEqual(by_side["HOME"]["possession_pct"], 61)
        self.assertEqual(by_side["HOME"]["expected_goals"], 1.84)

        self.assertEqual(
            by_side["HOME"]["opponent_name"],
            "Away FC",
        )
        self.assertEqual(
            by_side["AWAY"]["opponent_name"],
            "Home FC",
        )

        self.assertEqual(
            by_side["HOME"]["creates_signal"],
            "false",
        )
        self.assertEqual(
            by_side["HOME"]["probability_mutation"],
            "false",
        )

    def test_missing_metric_is_not_zero_filled(self):
        payload = complete_payload()
        payload["response"][0]["statistics"] = [
            {"type": "Total Shots", "value": 8}
        ]
        payload["response"][1]["statistics"] = [
            {"type": "Total Shots", "value": 5}
        ]

        rows = s81.normalize_team_statistics(
            payload,
            fixture(),
            "2026-09-17T12:00:00Z",
        )

        self.assertEqual(len(rows), 2)

        home = next(row for row in rows if row["side"] == "HOME")
        self.assertEqual(home["shots_total"], 8)
        self.assertEqual(home["expected_goals"], "")
        self.assertEqual(home["possession_pct"], "")

    def test_incomplete_one_team_payload_is_retryable(self):
        payload = complete_payload()
        payload["response"] = payload["response"][:1]

        rows = s81.normalize_team_statistics(
            payload,
            fixture(),
            "2026-09-17T12:00:00Z",
        )

        self.assertEqual(rows, [])

    def test_unknown_team_cannot_infer_venue(self):
        payload = complete_payload()
        payload["response"][0]["team"]["name"] = "Different FC"

        rows = s81.normalize_team_statistics(
            payload,
            fixture(),
            "2026-09-17T12:00:00Z",
        )

        self.assertEqual(rows, [])

    def test_merge_is_idempotent_first_observation_wins(self):
        original = s81.normalize_team_statistics(
            complete_payload(),
            fixture(),
            "2026-09-17T12:00:00Z",
        )

        later = [dict(row) for row in original]
        later[0]["shots_total"] = 999
        later[0]["observed_at_utc"] = "2026-09-18T12:00:00Z"

        merged = s81.merge_rows(original, later)

        self.assertEqual(len(merged), 2)

        home = next(row for row in merged if row["side"] == "HOME")
        self.assertEqual(home["shots_total"], 14)
        self.assertEqual(
            home["observed_at_utc"],
            "2026-09-17T12:00:00Z",
        )

    def test_completed_requires_both_sides(self):
        rows = s81.normalize_team_statistics(
            complete_payload(),
            fixture(),
            "2026-09-17T12:00:00Z",
        )

        self.assertEqual(
            s81.completed_fixture_ids(rows),
            {"100"},
        )

        self.assertEqual(
            s81.completed_fixture_ids(rows[:1]),
            set(),
        )

    def test_never_attempted_candidate_precedes_retry(self):
        rows = [
            {
                **fixture("100"),
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "2026-09-17T10:00:00Z",
            },
            {
                **fixture("200"),
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "",
            },
        ]

        candidates = s81.candidate_fixtures(
            rows, set(), NOW, 2
        )

        self.assertEqual(
            [row["fixture_id"] for row in candidates],
            ["200", "100"],
        )

    def test_least_recent_retry_goes_first(self):
        rows = [
            {
                **fixture("100"),
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "2026-09-17T11:00:00Z",
            },
            {
                **fixture("200"),
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "2026-09-17T10:00:00Z",
            },
        ]

        candidates = s81.candidate_fixtures(
            rows, set(), NOW, 2
        )

        self.assertEqual(
            [row["fixture_id"] for row in candidates],
            ["200", "100"],
        )

    def test_capture_no_data_does_not_mark_captured(self):
        backlog = [
            {
                **fixture(),
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "",
            }
        ]

        calls = []

        def fake_get(path, params, **kwargs):
            calls.append((path, params, kwargs))
            return {"response": []}

        result = s81.capture(
            backlog,
            [],
            fake_get,
            NOW,
            1,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0][0],
            "/fixtures/statistics",
        )
        self.assertEqual(
            result["captured_fixtures"],
            0,
        )
        self.assertEqual(
            result["attempts"][0]["result"],
            "NO_DATA",
        )
        self.assertEqual(result["rows"], [])

    def test_capture_complete_payload(self):
        backlog = [
            {
                **fixture(),
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "",
            }
        ]

        def fake_get(path, params, **kwargs):
            self.assertEqual(path, "/fixtures/statistics")
            self.assertEqual(params, {"fixture": "100"})
            return complete_payload()

        result = s81.capture(
            backlog,
            [],
            fake_get,
            NOW,
            1,
        )

        self.assertEqual(
            result["captured_fixtures"],
            1,
        )
        self.assertEqual(
            result["captured_fixture_ids"],
            ["100"],
        )
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(
            result["attempts"][0]["result"],
            "CAPTURED",
        )

    def test_protected_budget_defers_without_false_attempt(self):
        backlog = [
            {
                **fixture(),
                "backlog_status": "PENDING",
                "last_attempt_at_utc": "",
            }
        ]

        def fake_get(path, params, **kwargs):
            raise audit.ProtectedBudgetError(
                "protected reserve"
            )

        result = s81.capture(
            backlog,
            [],
            fake_get,
            NOW,
            1,
        )

        self.assertEqual(
            result["captured_fixtures"],
            0,
        )
        self.assertEqual(
            result["deferred_fixtures"],
            1,
        )
        self.assertEqual(result["attempts"], [])
        self.assertTrue(result["warnings"])

    def test_no_candidate_means_zero_provider_calls(self):
        calls = []

        def fake_get(*args, **kwargs):
            calls.append((args, kwargs))
            return complete_payload()

        result = s81.capture(
            [],
            [],
            fake_get,
            NOW,
            2,
        )

        self.assertEqual(calls, [])
        self.assertEqual(
            result["candidate_fixtures"],
            0,
        )

    def test_no_data_retry_uses_exponential_cooldown(self):
        row = {
            **fixture("300"),
            "backlog_status": "PENDING",
            "attempt_count": "2",
            "last_attempt_result": "NO_DATA",
            "last_attempt_at_utc": "2026-09-17T05:00:00Z",
        }
        self.assertEqual(s81.retry_cooldown_hours(row), 12.0)
        self.assertEqual(s81.candidate_fixtures([row], set(), NOW, 10), [])
        later = datetime(2026, 9, 17, 17, 1, tzinfo=timezone.utc)
        ready = s81.candidate_fixtures([row], set(), later, 10)
        self.assertEqual([x["fixture_id"] for x in ready], ["300"])

    def test_no_data_cooldown_is_bounded(self):
        row = {
            **fixture("301"),
            "backlog_status": "PENDING",
            "attempt_count": "99",
            "last_attempt_result": "NO_DATA",
            "last_attempt_at_utc": "2026-09-17T10:00:00Z",
        }
        self.assertEqual(s81.retry_cooldown_hours(row), 72.0)


if __name__ == "__main__":
    unittest.main()
