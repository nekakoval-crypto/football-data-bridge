import unittest

from scripts.stage80_current_season_lineup_backfill import (
    current_season_lineup_tasks,
    current_season_number,
    rolling_terminal_fixture_map,
)


class TestCurrentSeasonLineupBackfill(unittest.TestCase):

    def test_current_season_is_max_provider_season(self):
        history = {
            "1": {"season": "2025"},
            "2": {"season": "2026"},
            "3": {"season": "2024"},
        }
        self.assertEqual(current_season_number(history), 2026)

    def test_rolling_archive_collapses_to_latest_fixture_observation(self):
        rows = [
            {
                "fixture_id": "100",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "country": "England",
                "season": "2026",
                "round": "Regular Season - 1",
                "kickoff_utc": "2026-08-15T14:00:00Z",
                "home_team": "A",
                "away_team": "B",
                "status": "scheduled",
                "source_status": "NS",
                "observed_at_utc": "2026-08-14T10:00:00Z",
            },
            {
                "fixture_id": "100",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "country": "England",
                "season": "2026",
                "round": "Regular Season - 1",
                "kickoff_utc": "2026-08-15T14:00:00Z",
                "home_team": "A",
                "away_team": "B",
                "status": "finished",
                "source_status": "FT",
                "observed_at_utc": "2026-08-15T17:00:00Z",
            },
        ]

        history = rolling_terminal_fixture_map(rows)

        self.assertEqual(set(history), {"100"})
        self.assertEqual(history["100"]["season"], "2026")
        self.assertEqual(
            history["100"]["provider_competition_id"],
            "39",
        )
        self.assertEqual(
            history["100"]["competition_name"],
            "Premier League",
        )
        self.assertEqual(history["100"]["status"], "FINISHED")
        self.assertEqual(history["100"]["source_status"], "FT")

    def test_latest_nonterminal_observation_is_not_eligible(self):
        rows = [
            {
                "fixture_id": "101",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "country": "England",
                "season": "2026",
                "round": "Regular Season - 2",
                "kickoff_utc": "2026-08-22T14:00:00Z",
                "home_team": "A",
                "away_team": "C",
                "status": "scheduled",
                "source_status": "NS",
                "observed_at_utc": "2026-08-20T10:00:00Z",
            }
        ]

        self.assertEqual(
            rolling_terminal_fixture_map(rows),
            {},
        )

    def test_raw_terminal_status_is_accepted(self):
        rows = [
            {
                "fixture_id": "102",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "country": "England",
                "season": "2026",
                "round": "Regular Season - 3",
                "kickoff_utc": "2026-08-29T14:00:00Z",
                "home_team": "A",
                "away_team": "D",
                "status": "",
                "source_status": "AET",
                "observed_at_utc": "2026-08-29T17:00:00Z",
            }
        ]

        history = rolling_terminal_fixture_map(rows)
        self.assertEqual(set(history), {"102"})

    def test_only_missing_lineups_in_current_season_and_newest_first(self):
        history = {
            "1": {
                "season": "2026",
                "kickoff_utc": "2026-08-01T10:00:00Z",
            },
            "2": {
                "season": "2026",
                "kickoff_utc": "2026-09-01T10:00:00Z",
            },
            "3": {
                "season": "2025",
                "kickoff_utc": "2026-05-01T10:00:00Z",
            },
        }

        state = {
            ("1", "/fixtures/lineups"): {
                "fixture_id": "1",
                "endpoint": "/fixtures/lineups",
                "season": "2026",
                "last_attempt_result": "CAPTURED",
            }
        }

        tasks = current_season_lineup_tasks(
            history,
            state,
            2026,
        )

        self.assertEqual(
            [row[0]["season"] for row in tasks],
            ["2026"],
        )
        self.assertEqual(
            [row[0]["kickoff_utc"] for row in tasks],
            ["2026-09-01T10:00:00Z"],
        )
        self.assertEqual(
            [row[1] for row in tasks],
            ["/fixtures/lineups"],
        )

    def test_no_data_is_terminal(self):
        history = {
            "1": {
                "season": "2026",
                "kickoff_utc": "2026-09-01T10:00:00Z",
            },
        }

        state = {
            ("1", "/fixtures/lineups"): {
                "fixture_id": "1",
                "endpoint": "/fixtures/lineups",
                "season": "2026",
                "last_attempt_result": "NO_DATA",
            }
        }

        self.assertEqual(
            current_season_lineup_tasks(
                history,
                state,
                2026,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
