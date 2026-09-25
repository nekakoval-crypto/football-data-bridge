from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage292_environmental_historical_backfill as m


class Stage292EnvironmentalHistoricalBackfillTests(unittest.TestCase):
    def test_trusted_bridge_fixture_requires_verified_identity_and_venue(self):
        base = {
            "api_fixture_id": "100",
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
        row = m.trusted_bridge_fixture(base, {"10"}, 2022)
        self.assertIsNotNone(row)
        self.assertEqual(row["round"], "HISTORICAL_BRIDGE")

        bad = dict(base, mapping_status="REVIEW")
        self.assertIsNone(m.trusted_bridge_fixture(bad, {"10"}, 2022))

        no_venue = dict(base, api_home_team_id="999")
        self.assertIsNone(m.trusted_bridge_fixture(no_venue, {"10"}, 2022))

    def test_eligible_bridge_fixtures_deduplicates_and_respects_min_season(self):
        rows = [
            {
                "api_fixture_id": "100",
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
        result = m.eligible_bridge_fixtures(rows, venues, 2022)
        self.assertEqual([r["fixture_id"] for r in result], ["100"])


if __name__ == "__main__":
    unittest.main()
