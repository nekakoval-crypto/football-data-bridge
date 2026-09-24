import unittest

from scripts.stage270_prematch_venue_state import (
    build_rows,
    prematch_evidence_by_fixture,
    roof_requirement,
    weather_exposure_resolution,
)


class PrematchVenueStateTests(unittest.TestCase):

    def test_retractable_requires_match_state(self):
        self.assertEqual(
            roof_requirement("RETRACTABLE_FULL_PITCH_COVER"),
            "PREMATCH_REQUIRED",
        )

    def test_closed_roof_shields_weather(self):
        self.assertEqual(
            weather_exposure_resolution(
                "RETRACTABLE_FULL_PITCH_COVER",
                "PREMATCH_REQUIRED",
                "CLOSED",
            ),
            "ROOF_CLOSED_WEATHER_SHIELDED",
        )

    def test_postkickoff_evidence_is_rejected(self):
        rows = [{
            "api_fixture_id": "10",
            "roof_state_actual": "CLOSED",
            "captured_at_utc": "2026-09-24T20:00:00Z",
            "kickoff_utc": "2026-09-24T19:00:00Z",
        }]
        self.assertEqual(prematch_evidence_by_fixture(rows), {})

    def test_latest_prematch_evidence_wins(self):
        rows = [
            {
                "api_fixture_id": "10",
                "roof_state_actual": "OPEN",
                "captured_at_utc": "2026-09-24T17:00:00Z",
                "kickoff_utc": "2026-09-24T19:00:00Z",
            },
            {
                "api_fixture_id": "10",
                "roof_state_actual": "CLOSED",
                "captured_at_utc": "2026-09-24T18:00:00Z",
                "kickoff_utc": "2026-09-24T19:00:00Z",
            },
        ]
        selected = prematch_evidence_by_fixture(rows)
        self.assertEqual(selected["10"]["roof_state_actual"], "CLOSED")

    def test_missing_dynamic_state_fails_closed(self):
        forward = [{
            "forward_id": "x",
            "rule": "R1",
            "api_fixture_id": "10",
            "home_team": "Home",
            "away_team": "Away",
            "status": "PAPER",
        }]
        context = [{
            "forward_id": "x",
            "captured_at_utc": "2026-09-24T10:00:00Z",
            "current_kickoff_utc": "2026-09-24T19:00:00Z",
            "home_team_id": "1",
            "home_team": "Home",
            "away_team": "Away",
        }]
        venues = [{
            "team_id": "1",
            "venue_id": "100",
            "venue_name": "Roof Arena",
            "roof_type": "RETRACTABLE_FULL_PITCH_COVER",
        }]

        row = build_rows(forward, context, venues, [])[0]

        self.assertEqual(row["roof_state_requirement"], "PREMATCH_REQUIRED")
        self.assertEqual(row["roof_state_actual"], "UNKNOWN")
        self.assertEqual(row["roof_state_capture_status"], "NOT_CAPTURED")
        self.assertEqual(row["usable_for_prematch"], "false")
        self.assertEqual(
            row["weather_exposure_resolution"],
            "UNRESOLVED_RETRACTABLE_ROOF_STATE",
        )


if __name__ == "__main__":
    unittest.main()
