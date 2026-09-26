import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

import stage77_historical_player_backfill as h


class HistoricalPlayerBackfillTests(unittest.TestCase):

    def fixture(
        self,
        fixture_id,
        season="2025",
        role="DOMESTIC_LEAGUE",
        comp="Premier League",
        country="England",
        comp_id="39",
    ):
        return {
            "fixture_id": str(fixture_id),
            "competition_role": role,
            "country": country,
            "provider_competition_id": comp_id,
            "competition_name": comp,
            "season": season,
            "round": "1",
            "kickoff_utc": (
                f"{season}-08-01T15:00:00+00:00"
            ),
            "status": "FT",
            "home_team": "A",
            "away_team": "B",
        }

    def test_no_data_is_not_requeued(self):
        history = {
            "1": self.fixture("1"),
            "2": self.fixture("2"),
        }

        state = {
            "1": {
                "fixture_id": "1",
                "last_attempt_result": "NO_DATA",
                "attempt_count": "1",
            }
        }

        rows = h.candidate_rows(
            history,
            captured=set(),
            state=state,
        )

        self.assertEqual(
            [r["fixture_id"] for r in rows],
            ["2"],
        )

    def test_captured_ledger_fixture_is_not_requeued(self):
        history = {
            "1": self.fixture("1"),
            "2": self.fixture("2"),
        }

        rows = h.candidate_rows(
            history,
            captured={"2"},
            state={},
        )

        self.assertEqual(
            [r["fixture_id"] for r in rows],
            ["1"],
        )

    def test_recent_domestic_league_has_priority(self):
        history = {
            "1": self.fixture(
                "1",
                season="2020",
                role="CUP",
                comp="FA Cup",
            ),
            "2": self.fixture(
                "2",
                season="2024",
                role="DOMESTIC_LEAGUE",
            ),
            "3": self.fixture(
                "3",
                season="2025",
                role="DOMESTIC_LEAGUE",
            ),
        }

        rows = h.candidate_rows(
            history,
            captured=set(),
            state={},
        )

        self.assertEqual(
            [r["fixture_id"] for r in rows],
            ["3", "2", "1"],
        )

    def test_apply_attempt_preserves_attempt_count(self):
        fixture = self.fixture("7")

        state = {
            "7": {
                "fixture_id": "7",
                "attempt_count": "2",
                "last_attempt_result": "ERROR",
            }
        }

        h.apply_attempt(
            state,
            fixture,
            result="CAPTURED",
            attempted_at="2026-09-20T00:00:00Z",
            player_rows=40,
        )

        self.assertEqual(
            state["7"]["attempt_count"],
            "3",
        )

        self.assertEqual(
            state["7"]["last_attempt_result"],
            "CAPTURED",
        )

        self.assertEqual(
            state["7"]["player_rows"],
            "40",
        )


    def test_empty_competition_season_is_suppressed_after_threshold(self):
        history = {
            str(i): self.fixture(
                str(i),
                comp="Virsliga",
                country="Latvia",
                comp_id="365",
            )
            for i in range(1, 11)
        }

        state = {
            str(i): {
                **history[str(i)],
                "attempt_count": "1",
                "last_attempt_result": "NO_DATA",
            }
            for i in range(1, 9)
        }

        rows = h.candidate_rows(
            history,
            captured=set(),
            state=state,
            no_data_cell_threshold=8,
        )

        self.assertEqual(rows, [])

    def test_productive_cell_is_not_suppressed_by_no_data(self):
        history = {
            "1": self.fixture("1"),
            "2": self.fixture("2"),
            "3": self.fixture("3"),
        }

        state = {
            "1": {
                **history["1"],
                "attempt_count": "1",
                "last_attempt_result": "CAPTURED",
            },
            "2": {
                **history["2"],
                "attempt_count": "1",
                "last_attempt_result": "NO_DATA",
            },
        }

        rows = h.candidate_rows(
            history,
            captured={"1"},
            state=state,
            no_data_cell_threshold=1,
        )

        self.assertEqual(
            [row["fixture_id"] for row in rows],
            ["3"],
        )


    def test_historical_player_backfill_requests_archive_first(self):
        fixture = self.fixture("1")
        calls = []

        def fake_get(path, params, **kwargs):
            calls.append((path, params, kwargs))
            return {"response": []}

        h.run_capture(
            [fixture],
            existing_stats=[],
            existing_grades=[],
            state={},
            get=fake_get,
            now=h.datetime(2026, 9, 20, tzinfo=h.timezone.utc),
            limit=1,
            no_data_cell_threshold=8,
        )

        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][2]["archive_first"])
        self.assertFalse(calls[0][2]["force_refresh"])

    def test_archive_hit_can_bypass_budget_wrapper(self):
        calls = []
        stats = {
            "archive_read_hits": 0,
            "archive_read_misses": 0,
            "archive_read_errors": 0,
        }

        def budget(path, params=None, **kwargs):
            calls.append((path, params, kwargs))
            raise AssertionError("budget must not be touched on archive hit")

        archived = {"response": []}
        get = h.make_archive_before_budget_get(
            budget,
            stats,
            archive_reader=lambda key: archived,
        )

        result = h.run_capture(
            [self.fixture("1")],
            existing_stats=[],
            existing_grades=[],
            state={},
            get=get,
            now=h.datetime(2026, 9, 20, tzinfo=h.timezone.utc),
            limit=1,
            no_data_cell_threshold=8,
        )

        self.assertEqual(calls, [])
        self.assertEqual(stats["archive_read_hits"], 1)
        self.assertEqual(stats["archive_read_misses"], 0)
        self.assertEqual(result["no_data_fixtures"], 1)

    def test_dual_lane_reserves_legacy_share(self):
        candidates = [
            self.fixture("r1", season="2025"),
            self.fixture("r2", season="2025"),
            self.fixture("r3", season="2024"),
            self.fixture("r4", season="2024"),
            self.fixture("o1", season="2023"),
            self.fixture("o2", season="2022"),
            self.fixture("o3", season="2021"),
            self.fixture("o4", season="2020"),
        ]

        plan = h.plan_dual_lane(
            candidates,
            state={},
            limit=5,
            legacy_share=0.40,
            recent_season_window=1,
        )

        seasons = [int(row["season"]) for row in plan["rows"]]
        self.assertEqual(plan["recent_planned"], 3)
        self.assertEqual(plan["legacy_planned"], 2)
        self.assertEqual(sum(season <= 2023 for season in seasons), 2)

    def test_dual_lane_interleaves_legacy_before_end_of_batch(self):
        candidates = [
            self.fixture(f"r{i}", season="2025")
            for i in range(1, 7)
        ] + [
            self.fixture(f"o{i}", season="2020")
            for i in range(1, 5)
        ]

        plan = h.plan_dual_lane(
            candidates,
            state={},
            limit=10,
            legacy_share=0.40,
            recent_season_window=1,
        )

        first_five = plan["rows"][:5]
        self.assertGreaterEqual(
            sum(int(row["season"]) < 2024 for row in first_five),
            1,
        )
        self.assertEqual(plan["legacy_planned"], 4)

    def test_legacy_lane_prefers_productive_cell_then_oldest(self):
        productive_old = self.fixture(
            "p",
            season="2021",
            comp="Old Productive",
            comp_id="100",
        )
        unproven_older = self.fixture(
            "u",
            season="2018",
            comp="Older Unproven",
            comp_id="200",
        )
        recent = self.fixture("r", season="2025", comp_id="39")

        state = {
            "proof": {
                **self.fixture(
                    "proof",
                    season="2021",
                    comp="Old Productive",
                    comp_id="100",
                ),
                "last_attempt_result": "CAPTURED",
            }
        }

        plan = h.plan_dual_lane(
            [recent, productive_old, unproven_older],
            state=state,
            limit=2,
            legacy_share=0.50,
            recent_season_window=1,
        )

        legacy_rows = [
            row for row in plan["rows"]
            if int(row["season"]) < 2024
        ]
        self.assertEqual([row["fixture_id"] for row in legacy_rows], ["p"])

    def test_captured_state_without_normalized_ledgers_is_replayed(self):
        fixture = self.fixture("123", season="2024")
        history = {"123": fixture}
        state = {
            "123": {
                **fixture,
                "last_attempt_result": "CAPTURED",
                "attempt_count": "1",
            }
        }

        candidates = h.candidate_rows(
            history,
            captured=set(),
            state=state,
            no_data_cell_threshold=8,
        )

        self.assertEqual([row["fixture_id"] for row in candidates], ["123"])

    def test_no_data_state_remains_terminal_without_normalized_ledgers(self):
        fixture = self.fixture("124", season="2024")
        history = {"124": fixture}
        state = {
            "124": {
                **fixture,
                "last_attempt_result": "NO_DATA",
                "attempt_count": "1",
            }
        }

        candidates = h.candidate_rows(
            history,
            captured=set(),
            state=state,
            no_data_cell_threshold=8,
        )

        self.assertEqual(candidates, [])

    def test_provider_quota_error_stops_batch_immediately(self):
        candidates = [
            self.fixture("1"),
            self.fixture("2"),
            self.fixture("3"),
        ]

        calls = []

        def fake_get(path, params, **kwargs):
            calls.append(params["fixture"])
            raise h.ApiFootballBrokerError(
                "API-Football HTTP 429 for /fixtures/players"
            )

        result = h.run_capture(
            candidates,
            existing_stats=[],
            existing_grades=[],
            state={},
            get=fake_get,
            now=h.datetime(
                2026,
                9,
                20,
                tzinfo=h.timezone.utc,
            ),
            limit=3,
            no_data_cell_threshold=8,
        )

        self.assertEqual(calls, ["1"])
        self.assertEqual(result["attempted_fixtures"], 1)
        self.assertEqual(result["error_fixtures"], 1)
        self.assertTrue(result["provider_quota_exhausted"])
        self.assertEqual(result["deferred_fixtures"], 2)

    def test_runtime_empty_cell_stops_sampling_and_moves_on(self):
        empty = [
            self.fixture(
                str(i),
                comp="Virsliga",
                country="Latvia",
                comp_id="365",
            )
            for i in range(1, 6)
        ]
        second_cell = self.fixture(
            "100",
            comp="Eliteserien",
            country="Norway",
            comp_id="103",
        )
        candidates = empty + [second_cell]
        calls = []

        def fake_get(path, params, **kwargs):
            calls.append(params["fixture"])
            return {"response": []}

        result = h.run_capture(
            candidates,
            existing_stats=[],
            existing_grades=[],
            state={},
            get=fake_get,
            now=h.datetime(
                2026,
                9,
                20,
                tzinfo=h.timezone.utc,
            ),
            limit=4,
            no_data_cell_threshold=2,
        )

        self.assertEqual(calls, ["1", "2", "100"])
        self.assertEqual(result["attempted_fixtures"], 3)
        self.assertEqual(result["no_data_fixtures"], 3)
        self.assertEqual(
            result["suppressed_empty_cell_fixtures"],
            3,
        )


if __name__ == "__main__":
    unittest.main()
