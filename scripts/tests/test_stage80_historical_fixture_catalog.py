import unittest

import scripts.stage80_historical_fixture_catalog as catalog


class Stage80HistoricalFixtureCatalogTests(unittest.TestCase):
    def test_multi_observation_fixture_tracks_status_score_and_reschedule(self):
        rows = [
            {"fixture_id":"10","provider_league_id":"135","league_name":"Serie A","season":"2026","round":"R1","kickoff_utc":"2026-09-15T18:00:00Z","home_team":"A","away_team":"B","status":"scheduled","source_status":"NS","observed_at_utc":"2026-09-10T10:00:00Z"},
            {"fixture_id":"10","provider_league_id":"135","league_name":"Serie A","season":"2026","round":"R1","kickoff_utc":"2026-09-16T18:00:00Z","home_team":"A","away_team":"B","status":"scheduled","source_status":"NS","observed_at_utc":"2026-09-11T10:00:00Z"},
            {"fixture_id":"10","provider_league_id":"135","league_name":"Serie A","season":"2026","round":"R1","kickoff_utc":"2026-09-16T18:00:00Z","home_team":"A","away_team":"B","status":"finished","source_status":"FT","score_home":"2","score_away":"1","observed_at_utc":"2026-09-16T20:00:00Z"},
        ]
        result, invalid = catalog.build_catalog(rows)
        self.assertEqual(invalid, 0)
        self.assertEqual(len(result), 1)
        row = result[0]
        self.assertEqual(row["first_kickoff_utc"], "2026-09-15T18:00:00Z")
        self.assertEqual(row["latest_kickoff_utc"], "2026-09-16T18:00:00Z")
        self.assertEqual(row["reschedule_observed"], "YES")
        self.assertEqual(row["observation_count"], "3")
        self.assertEqual(row["terminal_observed"], "YES")
        self.assertEqual((row["final_score_home"], row["final_score_away"]), ("2", "1"))

    def test_latest_nonterminal_does_not_erase_earlier_terminal_evidence(self):
        rows = [
            {"fixture_id":"20","kickoff_utc":"2026-09-15T18:00:00Z","status":"finished","source_status":"FT","score_home":"1","score_away":"0","observed_at_utc":"2026-09-15T20:00:00Z"},
            {"fixture_id":"20","kickoff_utc":"2026-09-15T18:00:00Z","status":"unknown","source_status":"","observed_at_utc":"2026-09-15T21:00:00Z"},
        ]
        result, _ = catalog.build_catalog(rows)
        self.assertEqual(result[0]["terminal_observed"], "YES")
        self.assertEqual(result[0]["terminal_observed_at_utc"], "2026-09-15T20:00:00Z")
        self.assertEqual(result[0]["final_score_home"], "1")

    def test_invalid_rows_are_reported_not_fabricated(self):
        result, invalid = catalog.build_catalog([
            {"fixture_id":"", "observed_at_utc":"2026-09-15T10:00:00Z"},
            {"fixture_id":"30", "observed_at_utc":""},
        ])
        self.assertEqual(result, [])
        self.assertEqual(invalid, 2)

    def test_projection_is_deterministic_independent_of_input_order(self):
        a = {"fixture_id":"2","kickoff_utc":"2026-09-15T12:00:00Z","observed_at_utc":"2026-09-15T10:00:00Z"}
        b = {"fixture_id":"1","kickoff_utc":"2026-09-15T12:00:00Z","observed_at_utc":"2026-09-15T10:00:00Z"}
        one, _ = catalog.build_catalog([a, b])
        two, _ = catalog.build_catalog([b, a])
        self.assertEqual(one, two)
        self.assertEqual([row["fixture_id"] for row in one], ["1", "2"])


if __name__ == "__main__":
    unittest.main()
