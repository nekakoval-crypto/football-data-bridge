from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage292_environmental_historical_backfill as m


class Stage292EnvironmentalHistoricalBackfillTests(unittest.TestCase):
    def test_market_ou25_historical_ids_accepts_avg_or_b365_pairs(self):
        rows = [
            {
                "historical_match_id": "a",
                "avg_close_over_25": "1.9",
                "avg_close_under_25": "1.95",
            },
            {
                "historical_match_id": "b",
                "b365_close_over_25": "2.1",
                "b365_close_under_25": "1.8",
            },
            {
                "historical_match_id": "c",
                "avg_close_over_25": "",
                "avg_close_under_25": "",
            },
        ]
        self.assertEqual(m.market_ou25_historical_ids(rows), {"a", "b"})

    def test_trusted_bridge_fixture_requires_verified_identity_and_venue(self):
        base = {
            "api_fixture_id": "100",
            "historical_match_id": "hm100",
            "provider_league_id": "39",
            "league_code": "E0",
            "season_start": "2024",
            "api_kickoff_utc": "2024-08-17T14:00:00Z",
            "api_home_team_id": "10",
            "api_home_team": "Home FC",
            "api_away_team_id": "20",
            "api_away_team": "Away FC",
            "mapping_status": "AUTO",
            "one_to_one_verified": "true",
            "fuzzy_string_matching_used": "false",
        }
        row = m.trusted_bridge_fixture(base, {"10"}, 2022, {"hm100"})
        self.assertIsNotNone(row)
        self.assertEqual(row["round"], "HISTORICAL_BRIDGE")

        bad = dict(base, mapping_status="REVIEW")
        self.assertIsNone(m.trusted_bridge_fixture(bad, {"10"}, 2022, {"hm100"}))

        no_venue = dict(base, api_home_team_id="999")
        self.assertIsNone(m.trusted_bridge_fixture(no_venue, {"10"}, 2022, {"hm100"}))

    def test_archive_hit_bypasses_provider_budget(self):
        calls = []
        stats = {"archive_read_hits": 0, "archive_read_misses": 0, "archive_read_errors": 0}

        def archive_reader(key):
            self.assertIn("/fixtures/statistics", key)
            return {"response": [{"team": {"id": 1, "name": "Home"}, "statistics": []}]}

        def fallback_get(path, params=None, **kwargs):
            calls.append((path, params, kwargs))
            raise AssertionError("provider budget must not be touched on archive hit")

        get = m.make_archive_first_get(fallback_get, stats, archive_reader=archive_reader)
        payload = get("/fixtures/statistics", {"fixture": "123"}, force_refresh=False)
        self.assertIsInstance(payload, dict)
        self.assertEqual(calls, [])
        self.assertEqual(stats["archive_read_hits"], 1)
        self.assertEqual(stats["archive_read_misses"], 0)

    def test_archive_miss_falls_back_once(self):
        calls = []
        stats = {"archive_read_hits": 0, "archive_read_misses": 0, "archive_read_errors": 0}

        def archive_reader(_key):
            return None

        def fallback_get(path, params=None, **kwargs):
            calls.append((path, params, kwargs))
            return {"response": []}

        get = m.make_archive_first_get(fallback_get, stats, archive_reader=archive_reader)
        payload = get("/fixtures/statistics", {"fixture": "123"}, archive_first=True)
        self.assertEqual(payload, {"response": []})
        self.assertEqual(len(calls), 1)
        self.assertNotIn("archive_first", calls[0][2])
        self.assertEqual(stats["archive_read_hits"], 0)
        self.assertEqual(stats["archive_read_misses"], 1)

    def test_eligible_bridge_fixtures_deduplicates_and_respects_min_season(self):
        rows = [
            {
                "api_fixture_id": "100",
                "historical_match_id": "hm100",
                "provider_league_id": "39",
                "league_code": "E0",
                "season_start": "2024",
                "api_kickoff_utc": "2024-08-17T14:00:00Z",
                "api_home_team_id": "10",
                "api_home_team": "Home FC",
                "api_away_team": "Away FC",
                "mapping_status": "HIGH",
                "one_to_one_verified": "true",
                "fuzzy_string_matching_used": "false",
            },
            {
                "api_fixture_id": "100",
                "historical_match_id": "hm100",
                "provider_league_id": "39",
                "league_code": "E0",
                "season_start": "2024",
                "api_kickoff_utc": "2024-08-17T14:00:00Z",
                "api_home_team_id": "10",
                "api_home_team": "Home FC",
                "api_away_team": "Away FC",
                "mapping_status": "HIGH",
                "one_to_one_verified": "true",
                "fuzzy_string_matching_used": "false",
            },
            {
                "api_fixture_id": "99",
                "historical_match_id": "hm99",
                "provider_league_id": "39",
                "league_code": "E0",
                "season_start": "2021",
                "api_kickoff_utc": "2021-08-17T14:00:00Z",
                "api_home_team_id": "10",
                "api_home_team": "Home FC",
                "api_away_team": "Away FC",
                "mapping_status": "AUTO",
                "one_to_one_verified": "true",
                "fuzzy_string_matching_used": "false",
            },
        ]
        venues = [{"team_id": "10"}]
        result = m.eligible_bridge_fixtures(rows, venues, 2022, {"hm100"})
        self.assertEqual([r["fixture_id"] for r in result], ["100"])


if __name__ == "__main__":
    unittest.main()
