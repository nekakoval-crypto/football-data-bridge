import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage56_weather_rotation as env
import stage56_latest_view as latest
from pbk_weather_evidence_gate import valid_weather_evidence


class EnvironmentContractTests(unittest.TestCase):

    def setUp(self):
        # Synthetic test evidence, not a real archived forecast.
        self.fixture = {
            "forward_id": "CAPTURE|1584430",
            "api_fixture_id": "1584430",
            "country": "Turkey",
            "status": "CAPTURE",
        }
        self.context = {
            "forward_id": "CAPTURE|1584430",
            "venue_city": "Diyarbakir",
            "current_kickoff_utc": "2026-10-17T12:00:00Z",
        }
        self.row = {
            "forward_id": "CAPTURE|1584430",
            "api_fixture_id": "1584430",
            "snapshot_type": "BASELINE",
            "country_code": "TR",
            "venue_city": "Diyarbakir",
            "geocoded_name": "Diyarbakir",
            "latitude": "37.91363",
            "longitude": "40.21721",
            "captured_at_utc": "2026-10-14T10:00:00Z",
            "kickoff_utc": "2026-10-17T12:00:00Z",
            "forecast_time_utc": "2026-10-17T12:00:00Z",
            "forecast_gap_minutes": "0",
            "evidence_time_status": "PREMATCH_FROZEN",
            "usable_for_prematch": "true",
        }

    def done(self, rows):
        return env.weather_done_keys(
            rows,
            [self.fixture],
            {self.fixture["forward_id"]: self.context},
        )

    def test_baseline_window(self):
        self.assertEqual(
            env.weather_due_type(set(), "x", 71), "BASELINE"
        )
        self.assertEqual(
            env.weather_due_type(set(), "x", 218), ""
        )
        self.assertEqual(
            env.weather_due_type(set(), "x", 73), ""
        )
        self.assertEqual(
            env.weather_due_type(set(), "x", -1), ""
        )

    def test_refresh_windows(self):
        completed = {("x", "BASELINE")}
        self.assertEqual(
            env.weather_due_type(completed, "x", 24), "T24"
        )
        completed.add(("x", "T24"))
        self.assertEqual(
            env.weather_due_type(completed, "x", 3), "T3"
        )
        completed.add(("x", "T3"))
        self.assertEqual(
            env.weather_due_type(completed, "x", 1), "T60"
        )
        completed.add(("x", "T60"))
        self.assertEqual(
            env.weather_due_type(completed, "x", 1), ""
        )

    def test_correct_evidence_accepted_in_both_paths(self):
        self.assertTrue(valid_weather_evidence(
            self.row, self.fixture, self.context
        ))
        self.assertTrue(env.valid_prematch_weather_row(
            self.row, self.fixture, self.context
        ))
        self.assertTrue(latest.valid_weather_row(
            self.row, self.fixture, self.context
        ))

    def test_invalid_historical_gap_fails_closed(self):
        row = dict(self.row, forecast_gap_minutes="10920")
        self.assertFalse(valid_weather_evidence(
            row, self.fixture, self.context
        ))
        self.assertEqual(self.done([row]), set())

    def test_valid_snapshot_blocks_duplicate_baseline(self):
        self.assertEqual(
            self.done([self.row]),
            {("CAPTURE|1584430", "BASELINE")},
        )

    def test_corrupt_snapshot_allows_recovery(self):
        row = dict(self.row, longitude="120.0")
        self.assertEqual(self.done([row]), set())
        self.assertEqual(
            env.weather_due_type(
                self.done([row]), "CAPTURE|1584430", 48
            ),
            "BASELINE",
        )

    def test_wrong_country_rejected(self):
        row = dict(self.row, country_code="PH")
        self.assertFalse(valid_weather_evidence(
            row, self.fixture, self.context
        ))

    def test_wrong_fixture_rejected(self):
        row = dict(self.row, api_fixture_id="9999999")
        self.assertFalse(valid_weather_evidence(
            row, self.fixture, self.context
        ))

    def test_wrong_verified_coordinates_rejected(self):
        row = dict(self.row, latitude="12.0")
        self.assertFalse(valid_weather_evidence(
            row, self.fixture, self.context
        ))

    def test_nonfinite_coordinates_rejected(self):
        row = dict(self.row, latitude="NaN")
        self.assertFalse(valid_weather_evidence(
            row, self.fixture, self.context
        ))

    def test_postkickoff_snapshot_rejected(self):
        row = dict(
            self.row,
            captured_at_utc="2026-10-17T12:00:00Z",
        )
        self.assertFalse(valid_weather_evidence(
            row, self.fixture, self.context
        ))

    def test_changed_kickoff_rejected(self):
        context = dict(
            self.context,
            current_kickoff_utc="2026-10-17T13:00:00Z",
        )
        self.assertFalse(valid_weather_evidence(
            self.row, self.fixture, context
        ))

    def test_missing_data_fails_closed(self):
        self.assertFalse(valid_weather_evidence(
            {}, self.fixture, self.context
        ))
        self.assertFalse(valid_weather_evidence(
            self.row, self.fixture, {}
        ))
        self.assertFalse(latest.valid_weather_row(
            {"forecast_gap_minutes": "0"}
        ))

    def test_prematch_freeze_contract(self):
        result = env.evidence_time_contract(
            "2026-10-14T10:00:00Z",
            "2026-10-17T12:00:00Z",
        )
        self.assertEqual(
            result["evidence_time_status"],
            "PREMATCH_FROZEN",
        )
        self.assertEqual(
            result["usable_for_prematch"], "true"
        )

    def test_postmatch_time_contract(self):
        result = env.evidence_time_contract(
            "2026-10-17T12:00:00Z",
            "2026-10-17T12:00:00Z",
        )
        self.assertEqual(
            result["usable_for_prematch"], "false"
        )

    def test_country_from_capture_not_league(self):
        examples = (
            ("Scotland", "GB"),
            ("Lithuania", "LT"),
            ("Latvia", "LV"),
            ("Turkey", "TR"),
            ("Austria", "AT"),
        )
        for country, expected in examples:
            with self.subTest(country=country):
                self.assertEqual(
                    env.country_code_for(
                        {"country": country},
                        {"league": "Bundesliga"},
                    ),
                    expected,
                )
        self.assertEqual(
            env.country_code_for(
                {},
                {"league": "Scottish Premiership"},
            ),
            "",
        )

    def test_weather_horizon_and_aq_source_horizon(self):
        self.assertEqual(
            env.WEATHER_BASELINE_MAX_HOURS, 72.0
        )
        self.assertEqual(
            env.AIR_QUALITY_MAX_HOURS, 144.0
        )
        self.assertGreater(
            env.AIR_QUALITY_MAX_HOURS,
            env.WEATHER_BASELINE_MAX_HOURS,
        )

    def test_altitude_contract(self):
        self.assertEqual(env.altitude_zone(""), "UNKNOWN")
        self.assertEqual(
            env.altitude_zone(50), "ALTITUDE_NORMAL"
        )
        self.assertEqual(
            env.altitude_zone(750), "ALTITUDE_ELEVATED"
        )
        self.assertEqual(
            env.altitude_zone(1250), "ALTITUDE_MATERIAL"
        )
        self.assertEqual(
            env.altitude_zone(1750), "ALTITUDE_HIGH"
        )
        self.assertEqual(
            env.altitude_zone(2200), "ALTITUDE_VERY_HIGH"
        )

    def test_thunderstorm_contract(self):
        self.assertEqual(
            env.thunderstorm_evidence(95), "YES"
        )
        self.assertEqual(
            env.thunderstorm_evidence(99), "YES"
        )
        self.assertEqual(
            env.thunderstorm_evidence(3), "NO"
        )
        self.assertEqual(
            env.thunderstorm_evidence(""), "UNKNOWN"
        )

    def test_exit_status_contract(self):
        for status, expected in (
            ("OK", 0), ("PARTIAL", 1),
            ("BLOCKED", 1), ("UNKNOWN", 1),
        ):
            with self.subTest(status=status):
                self.assertEqual(
                    env.pbk544_exit_code(status), expected
                )


if __name__ == "__main__":
    unittest.main()
