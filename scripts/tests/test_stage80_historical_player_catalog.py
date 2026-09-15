import unittest

import scripts.stage80_historical_player_catalog as catalog


class Stage80HistoricalPlayerCatalogTests(unittest.TestCase):
    def test_combines_roster_and_stats_evidence_without_current_team_claim(self):
        roster = [
            {"team_id":"100","team_name":"Alpha","captured_at_utc":"2026-09-01T00:00:00Z","player_id":"7","player_name":"Player Seven","age":"24","number":"9","position":"Attacker","photo_url":"p.jpg"},
            {"team_id":"100","team_name":"Alpha","captured_at_utc":"2026-09-08T00:00:00Z","player_id":"7","player_name":"Player Seven","age":"24","number":"9","position":"Attacker","photo_url":"p.jpg"},
        ]
        stats = [
            {"fixture_id":"50","team_id":"100","observed_at_utc":"2026-09-10T20:00:00Z","player_id":"7","player_name":"Player Seven","position":"F"},
            {"fixture_id":"51","team_id":"100","observed_at_utc":"2026-09-12T20:00:00Z","player_id":"7","player_name":"Player Seven","position":"F"},
        ]
        rows, bad_roster, bad_stats = catalog.build_catalog(roster, stats)
        self.assertEqual((bad_roster, bad_stats), (0, 0))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["player_id"], "7")
        self.assertEqual(row["first_seen_at_utc"], "2026-09-01T00:00:00Z")
        self.assertEqual(row["last_seen_at_utc"], "2026-09-12T20:00:00Z")
        self.assertEqual(row["roster_team_count"], "1")
        self.assertEqual(row["latest_roster_team_ids"], "100")
        self.assertEqual(row["stats_fixture_count"], "2")
        self.assertEqual(row["has_roster_evidence"], "YES")
        self.assertEqual(row["has_match_stats_evidence"], "YES")
        self.assertNotIn("current_team", row)

    def test_latest_roster_snapshot_preserves_multiple_observed_teams_instead_of_inference(self):
        roster = [
            {"team_id":"100","team_name":"Alpha","captured_at_utc":"2026-09-08T00:00:00Z","player_id":"7","player_name":"P"},
            {"team_id":"200","team_name":"Beta","captured_at_utc":"2026-09-08T00:00:00Z","player_id":"7","player_name":"P"},
        ]
        rows, _, _ = catalog.build_catalog(roster, [])
        self.assertEqual(rows[0]["latest_roster_team_ids"], "100,200")
        self.assertEqual(rows[0]["latest_roster_team_names"], "Alpha | Beta")
        self.assertEqual(rows[0]["roster_team_count"], "2")

    def test_stats_only_player_is_retained(self):
        stats = [
            {"fixture_id":"50","team_id":"100","observed_at_utc":"2026-09-10T20:00:00Z","player_id":"8","player_name":"Stats Only","position":"M"},
        ]
        rows, _, bad_stats = catalog.build_catalog([], stats)
        self.assertEqual(bad_stats, 0)
        self.assertEqual(rows[0]["player_id"], "8")
        self.assertEqual(rows[0]["has_roster_evidence"], "NO")
        self.assertEqual(rows[0]["has_match_stats_evidence"], "YES")
        self.assertEqual(rows[0]["latest_roster_team_ids"], "")

    def test_invalid_player_identity_rows_are_reported_not_fabricated(self):
        rows, bad_roster, bad_stats = catalog.build_catalog(
            [{"player_id":"", "captured_at_utc":"2026-09-01T00:00:00Z"}],
            [{"player_id":"", "observed_at_utc":"2026-09-01T00:00:00Z"}],
        )
        self.assertEqual(rows, [])
        self.assertEqual((bad_roster, bad_stats), (1, 1))

    def test_projection_is_deterministic_for_timestamped_evidence(self):
        roster_a = {"team_id":"200","team_name":"Beta","captured_at_utc":"2026-09-08T00:00:00Z","player_id":"7","player_name":"P","position":"M"}
        roster_b = {"team_id":"100","team_name":"Alpha","captured_at_utc":"2026-09-01T00:00:00Z","player_id":"7","player_name":"P","position":"M"}
        stat_a = {"fixture_id":"51","observed_at_utc":"2026-09-12T20:00:00Z","player_id":"7","player_name":"P","position":"M"}
        stat_b = {"fixture_id":"50","observed_at_utc":"2026-09-10T20:00:00Z","player_id":"7","player_name":"P","position":"M"}
        one, _, _ = catalog.build_catalog([roster_a, roster_b], [stat_a, stat_b])
        two, _, _ = catalog.build_catalog([roster_b, roster_a], [stat_b, stat_a])
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
