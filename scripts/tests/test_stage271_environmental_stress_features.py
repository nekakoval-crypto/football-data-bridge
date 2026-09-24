import unittest

from scripts.stage271_environmental_stress_features import build_feature_row


class EnvironmentalStressFeatureTests(unittest.TestCase):

    def base_weather(self, **extra):
        row = {
            "forward_id": "x",
            "rule": "R1",
            "api_fixture_id": "10",
            "kickoff_utc": "2026-09-24T19:00:00Z",
            "home_team": "Home",
            "away_team": "Away",
            "weather_snapshot_type": "T3",
            "weather_captured_at_utc": "2026-09-24T16:00:00Z",
            "weather_evidence_time_status": "PREMATCH_FROZEN",
            "weather_usable_for_prematch": "true",
            "temperature_c": "28",
            "apparent_temperature_c": "31",
            "relative_humidity_pct": "75",
            "dew_point_c": "22",
            "wind_speed_10m_kmh": "20",
            "wind_gusts_10m_kmh": "35",
            "precipitation_probability_pct": "60",
            "precipitation_mm": "2",
            "rain_mm": "2",
            "showers_mm": "0",
            "snowfall_cm": "0",
            "visibility_m": "10000",
            "weather_code": "61",
            "thunderstorm_evidence": "NO",
            "air_quality_status": "CAPTURED",
            "pm10_ug_m3": "12",
            "pm2_5_ug_m3": "6",
            "elevation_m": "120",
            "altitude_zone": "ALTITUDE_NORMAL",
        }
        row.update(extra)
        return row

    def venue(self, **extra):
        row = {
            "forward_id": "x",
            "venue_id": "100",
            "venue_name": "Example",
            "roof_type": "ALL_STANDS_COVERED_OPEN_PITCH",
            "roof_state_actual": "UNKNOWN",
            "roof_state_capture_status": "NOT_REQUIRED",
            "weather_exposure_resolution": "OPEN_PITCH_WEATHER_EXPOSED",
        }
        row.update(extra)
        return row

    def test_prematch_weather_projects_research_features(self):
        row = build_feature_row(self.base_weather(), self.venue(), "grass")
        self.assertEqual(row["environment_feature_state"], "RESEARCH_FEATURES_AVAILABLE")
        self.assertEqual(row["thermal_group_status"], "KNOWN")
        self.assertEqual(row["heat_humidity_joint_status"], "KNOWN_PAIR")
        self.assertEqual(row["apparent_temperature_delta_c"], "3")
        self.assertEqual(row["wind_gust_spread_kmh"], "15")
        self.assertEqual(row["predictive_authority"], "NOT_AUTHORIZED")

    def test_missing_weather_is_not_zero_filled(self):
        row = build_feature_row(
            {
                "forward_id": "x",
                "weather_usable_for_prematch": "",
                "weather_evidence_time_status": "",
            },
            self.venue(),
            "grass",
        )
        self.assertEqual(row["environment_feature_state"], "DATA_MISSING_WEATHER")
        self.assertEqual(row["thermal_group_status"], "UNKNOWN")
        self.assertEqual(row["temperature_c"], "")
        self.assertEqual(row["known_factor_groups"], "2")

    def test_postmatch_weather_is_rejected_as_feature_input(self):
        row = build_feature_row(
            self.base_weather(
                weather_evidence_time_status="POSTMATCH_FACTUAL",
                weather_usable_for_prematch="false",
            ),
            self.venue(),
            "grass",
        )
        self.assertEqual(row["environment_feature_state"], "DATA_MISSING_WEATHER")
        self.assertEqual(row["thermal_group_status"], "UNKNOWN")

    def test_retractable_unknown_state_stays_unresolved(self):
        row = build_feature_row(
            self.base_weather(),
            self.venue(
                roof_type="RETRACTABLE_FULL_PITCH_COVER",
                roof_state_capture_status="NOT_CAPTURED",
                weather_exposure_resolution="UNRESOLVED_RETRACTABLE_ROOF_STATE",
            ),
            "grass",
        )
        self.assertEqual(
            row["environment_feature_state"],
            "RESEARCH_FEATURES_WITH_UNRESOLVED_VENUE_STATE",
        )
        self.assertEqual(
            row["venue_environment_status"],
            "UNRESOLVED_RETRACTABLE_ROOF_STATE",
        )

    def test_closed_retractable_roof_is_explicit(self):
        row = build_feature_row(
            self.base_weather(),
            self.venue(
                roof_type="RETRACTABLE_FULL_PITCH_COVER",
                roof_state_actual="CLOSED",
                roof_state_capture_status="CAPTURED",
                weather_exposure_resolution="ROOF_CLOSED_WEATHER_SHIELDED",
            ),
            "grass",
        )
        self.assertEqual(row["venue_environment_status"], "ROOF_CLOSED")

    def test_no_aggregate_environment_score_exists(self):
        row = build_feature_row(self.base_weather(), self.venue(), "grass")
        self.assertNotIn("environment_score", row)
        self.assertIn("NO_AGGREGATE_SCORE", row["double_counting_policy"])
        self.assertEqual(row["probability_mutation"], "false")
        self.assertEqual(row["stake_changes"], "false")


if __name__ == "__main__":
    unittest.main()
