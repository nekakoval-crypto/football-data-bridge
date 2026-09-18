import unittest

from scripts.stage80_lineup_injury_archive import build_archives


class Stage80LineupInjuryArchiveTests(unittest.TestCase):
    def test_builds_lineup_and_deduplicates_injuries(self):
        context = [{
            "api_fixture_id": "100",
            "captured_at_utc": "2026-09-18T10:00:00Z",
            "current_kickoff_utc": "2026-09-18T12:00:00Z",
            "snapshot_type": "T60",
            "lineups_available": "YES",
            "home_team_id": "1",
            "home_team": "Home",
            "away_team_id": "2",
            "away_team": "Away",
            "home_formation": "4-3-3",
            "away_formation": "4-4-2",
            "home_coach": "H Coach",
            "away_coach": "A Coach",
            "home_start_xi_json": '[{"id":11,"name":"H1"},{"id":12,"name":"H2"}]',
            "away_start_xi_json": '[{"id":21,"name":"A1"}]',
            "injuries_json": (
                '[{"player_id":31,"player":"P","team_id":1,"team":"Home",'
                '"type":"Missing Fixture","reason":"Knee Injury"},'
                '{"player_id":31,"player":"P","team_id":1,"team":"Home",'
                '"type":"Missing Fixture","reason":"Knee Injury"}]'
            ),
        }]
        lineups, injuries = build_archives(context, [])
        self.assertEqual(len(lineups["rows"]), 2)
        self.assertEqual(lineups["added_rows"], 2)
        self.assertEqual(len(injuries["rows"]), 1)
        self.assertEqual(injuries["added_rows"], 1)

    def test_rotation_lineups_are_separate_provenance(self):
        rotation = [{
            "api_fixture_id": "100",
            "captured_at_utc": "2026-09-18T10:05:00Z",
            "kickoff_utc": "2026-09-18T12:00:00Z",
            "current_lineups_available": "YES",
            "home_team_id": "1",
            "home_team": "Home",
            "away_team_id": "2",
            "away_team": "Away",
            "home_current_formation": "4-3-3",
            "away_current_formation": "4-4-2",
            "home_current_coach": "H Coach",
            "away_current_coach": "A Coach",
            "home_current_xi_json": '[{"id":11,"name":"H1"}]',
            "away_current_xi_json": '[{"id":21,"name":"A1"}]',
        }]
        lineups, injuries = build_archives([], rotation)
        self.assertEqual(len(lineups["rows"]), 2)
        self.assertTrue(all(r["source_dataset"] == "rotation_snapshots" for r in lineups["rows"]))
        self.assertEqual(injuries["rows"], [])

    def test_append_only_rerun_is_idempotent(self):
        context = [{
            "api_fixture_id": "100",
            "captured_at_utc": "2026-09-18T10:00:00Z",
            "current_kickoff_utc": "2026-09-18T12:00:00Z",
            "snapshot_type": "T60",
            "lineups_available": "YES",
            "home_team_id": "1",
            "home_team": "Home",
            "away_team_id": "2",
            "away_team": "Away",
            "home_start_xi_json": '[{"id":11,"name":"H1"}]',
            "away_start_xi_json": '[{"id":21,"name":"A1"}]',
            "injuries_json": "[]",
        }]
        first, _ = build_archives(context, [])
        second, _ = build_archives(context, [], existing_lineups=first["rows"])
        self.assertEqual(second["added_rows"], 0)
        self.assertEqual(len(second["rows"]), 2)

    def test_missing_identity_is_reported_not_zero_filled(self):
        context = [{
            "api_fixture_id": "",
            "captured_at_utc": "2026-09-18T10:00:00Z",
            "current_kickoff_utc": "2026-09-18T12:00:00Z",
            "snapshot_type": "T60",
            "lineups_available": "YES",
            "home_team_id": "1",
            "home_team": "Home",
            "home_start_xi_json": '[{"id":11,"name":"H1"}]',
            "away_team_id": "",
            "away_team": "Away",
            "away_start_xi_json": "[]",
            "injuries_json": "[]",
        }]
        lineups, _ = build_archives(context, [])
        self.assertEqual(lineups["added_rows"], 0)
        self.assertGreaterEqual(lineups["invalid_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
