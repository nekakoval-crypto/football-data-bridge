import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import stage80_historical_lineup_injury_backfill as h


class HistoricalLineupInjuryBackfillTests(unittest.TestCase):

    def fixture(
        self,
        fixture_id,
        season="2025",
        country="England",
        comp_id="39",
        role="DOMESTIC_LEAGUE",
        status="FT",
    ):
        return {
            "fixture_id": str(fixture_id),
            "competition_role": role,
            "country": country,
            "provider_competition_id": comp_id,
            "competition_name": f"{country} League",
            "season": season,
            "round": "1",
            "kickoff_utc": f"{season}-08-01T15:00:00Z",
            "status": status,
            "home_team": "Home",
            "away_team": "Away",
        }

    def test_domestic_terminal_filter(self):
        rows = [
            self.fixture("1"),
            self.fixture("2", role="DOMESTIC_CUP"),
            self.fixture("3", status="NS"),
        ]
        history = h.domestic_terminal_fixture_map(rows)
        self.assertEqual(set(history), {"1"})

    def test_lineup_and_injury_tasks_created(self):
        history = {"1": self.fixture("1")}
        tasks = h.candidate_tasks(history, state={})
        self.assertEqual(
            [(row["fixture_id"], endpoint) for row, endpoint in tasks],
            [
                ("1", h.ENDPOINT_LINEUPS),
                ("1", h.ENDPOINT_INJURIES),
            ],
        )

    def test_candidate_tasks_are_interleaved_by_fixture(self):
        history = {
            "1": self.fixture("1", season="2025"),
            "2": self.fixture("2", season="2025"),
        }
        tasks = h.candidate_tasks(history, state={})
        self.assertEqual(
            [(row["fixture_id"], endpoint) for row, endpoint in tasks],
            [
                ("1", h.ENDPOINT_LINEUPS),
                ("1", h.ENDPOINT_INJURIES),
                ("2", h.ENDPOINT_LINEUPS),
                ("2", h.ENDPOINT_INJURIES),
            ],
        )

    def test_terminal_task_is_not_requeued(self):
        fixture = self.fixture("1")
        history = {"1": fixture}
        state = {
            h.state_key("1", h.ENDPOINT_LINEUPS): {
                **h.state_row_from_task(
                    fixture,
                    h.ENDPOINT_LINEUPS,
                ),
                "last_attempt_result": "CAPTURED",
            }
        }
        tasks = h.candidate_tasks(history, state)
        self.assertEqual(
            [endpoint for _, endpoint in tasks],
            [h.ENDPOINT_INJURIES],
        )

    def test_empty_injury_cell_is_suppressed_but_lineup_is_not(self):
        history = {
            str(i): self.fixture(
                str(i),
                country="Latvia",
                comp_id="365",
            )
            for i in range(1, 11)
        }
        state = {}
        for i in range(1, 9):
            fixture = history[str(i)]
            key = h.state_key(str(i), h.ENDPOINT_INJURIES)
            state[key] = {
                **h.state_row_from_task(
                    fixture,
                    h.ENDPOINT_INJURIES,
                ),
                "last_attempt_result": "NO_DATA",
                "attempt_count": "1",
            }

        tasks = h.candidate_tasks(
            history,
            state,
            injury_no_data_cell_threshold=8,
        )

        lineup_ids = [
            row["fixture_id"]
            for row, endpoint in tasks
            if endpoint == h.ENDPOINT_LINEUPS
        ]
        injury_ids = [
            row["fixture_id"]
            for row, endpoint in tasks
            if endpoint == h.ENDPOINT_INJURIES
        ]

        self.assertEqual(len(lineup_ids), 10)
        self.assertEqual(injury_ids, [])

    def test_productive_injury_cell_is_not_suppressed(self):
        fixture1 = self.fixture("1", country="Norway", comp_id="103")
        fixture2 = self.fixture("2", country="Norway", comp_id="103")
        history = {"1": fixture1, "2": fixture2}
        state = {
            h.state_key("1", h.ENDPOINT_INJURIES): {
                **h.state_row_from_task(
                    fixture1,
                    h.ENDPOINT_INJURIES,
                ),
                "last_attempt_result": "CAPTURED",
                "attempt_count": "1",
            }
        }

        tasks = h.candidate_tasks(
            history,
            state,
            injury_no_data_cell_threshold=1,
        )
        injury_ids = [
            row["fixture_id"]
            for row, endpoint in tasks
            if endpoint == h.ENDPOINT_INJURIES
        ]
        self.assertEqual(injury_ids, ["2"])

    def test_normalize_lineups(self):
        fixture = self.fixture("1")
        payload = {
            "response": [
                {
                    "team": {"id": 10, "name": "Home"},
                    "formation": "4-3-3",
                    "coach": {"id": 99, "name": "Coach"},
                    "startXI": [
                        {
                            "player": {
                                "id": 1,
                                "name": "P1",
                                "number": 9,
                                "pos": "F",
                                "grid": "1:1",
                            }
                        }
                    ],
                    "substitutes": [
                        {
                            "player": {
                                "id": 2,
                                "name": "P2",
                                "number": 10,
                                "pos": "M",
                            }
                        }
                    ],
                }
            ]
        }
        rows, response_rows = h.normalize_lineups(
            payload,
            fixture,
            "2026-09-20T20:00:00Z",
        )
        self.assertEqual(response_rows, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["side"], "HOME")
        self.assertEqual(rows[0]["starting_xi_count"], "1")
        self.assertEqual(rows[0]["substitutes_count"], "1")
        self.assertEqual(
            rows[0]["temporal_authority"],
            "RETROSPECTIVE_ONLY",
        )

    def test_normalize_injuries_deduplicates(self):
        fixture = self.fixture("1")
        item = {
            "team": {"id": 10, "name": "Home"},
            "player": {
                "id": 3,
                "name": "P3",
                "type": "Missing Fixture",
                "reason": "Hamstring",
            },
        }
        rows, response_rows = h.normalize_injuries(
            {"response": [item, item]},
            fixture,
            "2026-09-20T20:00:00Z",
        )
        self.assertEqual(response_rows, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["player_id"], "3")


    def test_historical_lineup_injury_requests_archive_first(self):
        calls = []

        def fake_get(path, params, **kwargs):
            calls.append((path, params, kwargs))
            return {"response": []}

        h.provider_get_with_timeout(
            fake_get,
            h.ENDPOINT_LINEUPS,
            "123",
            timeout_seconds=0,
        )

        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][2]["archive_first"])
        self.assertFalse(calls[0][2]["force_refresh"])

    def test_quota_error_stops_batch(self):
        tasks = [
            (self.fixture("1"), h.ENDPOINT_LINEUPS),
            (self.fixture("2"), h.ENDPOINT_LINEUPS),
        ]
        calls = []

        def fake_get(path, params, **kwargs):
            calls.append((path, params["fixture"]))
            raise h.ApiFootballBrokerError(
                "API-Football HTTP 429 for /fixtures/lineups"
            )

        result = h.run_capture(
            tasks,
            existing_lineups=[],
            existing_injuries=[],
            state={},
            get=fake_get,
            now=datetime(2026, 9, 20, tzinfo=timezone.utc),
            limit=10,
            injury_no_data_cell_threshold=8,
        )

        self.assertEqual(len(calls), 1)
        self.assertTrue(result["provider_quota_exhausted"])
        self.assertEqual(result["attempted_tasks"], 1)

    def test_runtime_injury_empty_cell_suppression(self):
        tasks = []
        for i in range(1, 5):
            tasks.append(
                (
                    self.fixture(
                        str(i),
                        country="Poland",
                        comp_id="106",
                    ),
                    h.ENDPOINT_INJURIES,
                )
            )

        calls = []

        def fake_get(path, params, **kwargs):
            calls.append(params["fixture"])
            return {"response": []}

        result = h.run_capture(
            tasks,
            existing_lineups=[],
            existing_injuries=[],
            state={},
            get=fake_get,
            now=datetime(2026, 9, 20, tzinfo=timezone.utc),
            limit=10,
            injury_no_data_cell_threshold=2,
        )

        self.assertEqual(calls, ["1", "2"])
        self.assertEqual(result["no_data_injury_tasks"], 2)
        self.assertEqual(result["suppressed_injury_tasks"], 2)


    def test_provider_timeout_triggers_watchdog(self):
        tasks = [
            (self.fixture("1"), h.ENDPOINT_LINEUPS),
            (self.fixture("2"), h.ENDPOINT_LINEUPS),
        ]

        def slow_get(path, params, **kwargs):
            time.sleep(0.2)
            return {"response": []}

        result = h.run_capture(
            tasks,
            existing_lineups=[],
            existing_injuries=[],
            state={},
            get=slow_get,
            now=datetime(2026, 9, 20, tzinfo=timezone.utc),
            limit=10,
            provider_timeout_seconds=0.05,
            max_consecutive_errors=1,
            heartbeat_every=1,
        )

        self.assertEqual(result["attempted_tasks"], 1)
        self.assertEqual(result["error_lineup_tasks"], 1)
        self.assertTrue(
            any("watchdog stopped batch" in x for x in result["warnings"])
        )


if __name__ == "__main__":
    unittest.main()