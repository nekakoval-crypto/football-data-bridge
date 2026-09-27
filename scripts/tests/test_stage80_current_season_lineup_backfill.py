import unittest

from scripts.stage80_current_season_lineup_backfill import (
    current_season_lineup_tasks,
    current_season_number,
)


class TestCurrentSeasonLineupBackfill(unittest.TestCase):
    def test_current_season_is_max_provider_season(self):
        history = {
            "1": {"season": "2025"},
            "2": {"season": "2026"},
            "3": {"season": "2024"},
        }
        self.assertEqual(current_season_number(history), 2026)

    def test_only_missing_lineups_in_current_season_and_newest_first(self):
        history = {
            "1": {"season": "2026", "kickoff_utc": "2026-08-01T10:00:00Z"},
            "2": {"season": "2026", "kickoff_utc": "2026-09-01T10:00:00Z"},
            "3": {"season": "2025", "kickoff_utc": "2026-05-01T10:00:00Z"},
        }
        state = {
            ("1", "/fixtures/lineups"): {
                "fixture_id": "1",
                "endpoint": "/fixtures/lineups",
                "season": "2026",
                "last_attempt_result": "CAPTURED",
            }
        }
        tasks = current_season_lineup_tasks(history, state, 2026)
        self.assertEqual([row[0]["season"] for row in tasks], ["2026"])
        self.assertEqual([row[0]["kickoff_utc"] for row in tasks], ["2026-09-01T10:00:00Z"])
        self.assertEqual([row[1] for row in tasks], ["/fixtures/lineups"])

    def test_no_data_is_terminal(self):
        history = {
            "1": {"season": "2026", "kickoff_utc": "2026-09-01T10:00:00Z"},
        }
        state = {
            ("1", "/fixtures/lineups"): {
                "fixture_id": "1",
                "endpoint": "/fixtures/lineups",
                "season": "2026",
                "last_attempt_result": "NO_DATA",
            }
        }
        self.assertEqual(current_season_lineup_tasks(history, state, 2026), [])


if __name__ == "__main__":
    unittest.main()
