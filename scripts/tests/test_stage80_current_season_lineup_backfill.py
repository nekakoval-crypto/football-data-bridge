import unittest

from scripts.stage80_current_season_lineup_backfill import (
    current_provider_season,
    current_season_lineup_tasks,
    latest_current_season_terminal_history,
)


class TestCurrentSeasonLineupBackfill(unittest.TestCase):
    def test_current_provider_season_comes_from_current_round(self):
        current = [
            {"season": "2025"},
            {"season": "2026"},
        ]
        self.assertEqual(current_provider_season(current), 2026)

    def test_fixture_history_uses_latest_observation_and_terminal_only(self):
        history = [
            {
                "fixture_id": "1",
                "season": "2026",
                "observed_at_utc": "2026-08-01T12:00:00Z",
                "status": "scheduled",
                "source_status": "NS",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "country": "England",
                "round": "Regular Season - 1",
                "kickoff_utc": "2026-08-01T14:00:00Z",
                "home_team": "A",
                "away_team": "B",
            },
            {
                "fixture_id": "1",
                "season": "2026",
                "observed_at_utc": "2026-08-01T17:00:00Z",
                "status": "finished",
                "source_status": "FT",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "country": "England",
                "round": "Regular Season - 1",
                "kickoff_utc": "2026-08-01T14:00:00Z",
                "home_team": "A",
                "away_team": "B",
            },
            {
                "fixture_id": "2",
                "season": "2026",
                "observed_at_utc": "2026-08-01T17:00:00Z",
                "status": "scheduled",
                "source_status": "NS",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "country": "England",
                "round": "Regular Season - 1",
                "kickoff_utc": "2026-08-02T14:00:00Z",
                "home_team": "C",
                "away_team": "D",
            },
            {
                "fixture_id": "3",
                "season": "2025",
                "observed_at_utc": "2026-05-01T17:00:00Z",
                "status": "finished",
                "source_status": "FT",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "country": "England",
                "round": "Regular Season - 38",
                "kickoff_utc": "2026-05-01T14:00:00Z",
                "home_team": "E",
                "away_team": "F",
            },
        ]
        selected = latest_current_season_terminal_history(history, 2026)
        self.assertEqual(set(selected), {"1"})
        self.assertEqual(selected["1"]["provider_competition_id"], "39")
        self.assertEqual(selected["1"]["status"], "FT")

    def test_only_missing_current_season_lineups_and_newest_first(self):
        history = {
            "1": {"season": "2026", "kickoff_utc": "2026-08-01T10:00:00Z"},
            "2": {"season": "2026", "kickoff_utc": "2026-09-01T10:00:00Z"},
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
