import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage56_weather_rotation as env
import stage56_latest_view as latest


class EnvironmentContractTests(unittest.TestCase):

    def test_far_future_weather_is_not_captured(self):
        self.assertEqual(
            env.weather_due_type(
                set(),
                "x",
                env.WEATHER_BASELINE_MAX_HOURS + 1,
            ),
            "",
        )

    def test_valid_baseline_is_captured(self):
        self.assertEqual(
            env.weather_due_type(set(), "x", 218),
            "BASELINE",
        )

    def test_bad_historical_gap_fails_closed(self):
        self.assertFalse(
            latest.valid_weather_row({
                "forecast_gap_minutes": "10920",
                "captured_at_utc": "2026-09-24T10:00:00Z",
                "kickoff_utc": "2026-09-24T12:00:00Z",
            })
        )
        self.assertTrue(
            latest.valid_weather_row({
                "forecast_gap_minutes": "30",
                "captured_at_utc": "2026-09-24T10:00:00Z",
                "kickoff_utc": "2026-09-24T12:00:00Z",
            })
        )

    def test_prematch_freeze_contract(self):
        contract = env.evidence_time_contract(
            "2026-09-24T10:00:00Z",
            "2026-09-24T12:00:00Z",
        )
        self.assertEqual(contract["evidence_time_status"], "PREMATCH_FROZEN")
        self.assertEqual(contract["usable_for_prematch"], "true")

    def test_postkickoff_weather_is_not_prematch_usable(self):
        contract = env.evidence_time_contract(
            "2026-09-24T12:00:00Z",
            "2026-09-24T12:00:00Z",
        )
        self.assertEqual(contract["evidence_time_status"], "POSTMATCH_FACTUAL")
        self.assertEqual(contract["usable_for_prematch"], "false")

        self.assertFalse(
            latest.valid_weather_row({
                "forecast_gap_minutes": "0",
                "captured_at_utc": "2026-09-24T12:00:00Z",
                "kickoff_utc": "2026-09-24T12:00:00Z",
            })
        )

    def test_missing_timestamps_fail_closed(self):
        self.assertFalse(
            latest.valid_weather_row({
                "forecast_gap_minutes": "30",
                "captured_at_utc": "",
                "kickoff_utc": "",
            })
        )

    def test_altitude_contract(self):
        self.assertEqual(env.altitude_zone(""), "UNKNOWN")
        self.assertEqual(env.altitude_zone(50), "ALTITUDE_NORMAL")
        self.assertEqual(env.altitude_zone(750), "ALTITUDE_ELEVATED")
        self.assertEqual(env.altitude_zone(1250), "ALTITUDE_MATERIAL")
        self.assertEqual(env.altitude_zone(1750), "ALTITUDE_HIGH")
        self.assertEqual(env.altitude_zone(2200), "ALTITUDE_VERY_HIGH")

    def test_thunderstorm_contract(self):
        self.assertEqual(env.thunderstorm_evidence(95), "YES")
        self.assertEqual(env.thunderstorm_evidence(99), "YES")
        self.assertEqual(env.thunderstorm_evidence(3), "NO")
        self.assertEqual(env.thunderstorm_evidence(""), "UNKNOWN")

    def test_aq_horizon_is_shorter_than_weather(self):
        self.assertLess(
            env.AIR_QUALITY_MAX_HOURS,
            env.WEATHER_BASELINE_MAX_HOURS,
        )

    def test_pbk16_mapping_examples(self):
        self.assertEqual(
            env.country_code_for(
                {},
                {"league": "Scottish Premiership"},
            ),
            "GB",
        )
        self.assertEqual(
            env.country_code_for(
                {},
                {"league": "A Lyga"},
            ),
            "LT",
        )
        self.assertEqual(
            env.country_code_for(
                {},
                {"league": "Virsliga"},
            ),
            "LV",
        )


if __name__ == "__main__":
    unittest.main()
