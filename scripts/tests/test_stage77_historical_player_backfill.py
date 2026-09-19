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
    ):
        return {
            "fixture_id": str(fixture_id),
            "competition_role": role,
            "country": "England",
            "provider_competition_id": "39",
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


if __name__ == "__main__":
    unittest.main()
