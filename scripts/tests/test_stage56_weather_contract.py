import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage56_latest_view as latest
import stage56_weather_rotation as weather


class Stage56WeatherContractTests(unittest.TestCase):

    def test_far_future_baseline_is_not_due(self):
        self.assertEqual(
            weather.weather_due_type(
                set(),
                "fixture-x",
                weather.WEATHER_BASELINE_MAX_HOURS
                + 0.01,
            ),
            "",
        )

    def test_baseline_inside_horizon_is_due(self):
        self.assertEqual(
            weather.weather_due_type(
                set(),
                "fixture-x",
                218.0,
            ),
            "BASELINE",
        )

    def test_existing_baseline_does_not_block_t24(self):
        done = {
            ("fixture-x", "BASELINE"),
        }

        self.assertEqual(
            weather.weather_due_type(
                done,
                "fixture-x",
                24.0,
            ),
            "T24",
        )

    def test_latest_view_rejects_large_forecast_gap(self):
        self.assertFalse(
            latest.valid_weather_row({
                "forecast_gap_minutes": "10920.0",
            })
        )

        self.assertFalse(
            latest.valid_weather_row({
                "forecast_gap_minutes": "5340.0",
            })
        )

        self.assertTrue(
            latest.valid_weather_row({
                "forecast_gap_minutes": "30.0",
            })
        )

    def test_latest_view_fails_closed_on_missing_gap(self):
        self.assertFalse(
            latest.valid_weather_row({})
        )

        self.assertFalse(
            latest.valid_weather_row({
                "forecast_gap_minutes": "",
            })
        )

    def test_pbk16_country_mapping(self):
        expected = {
            "Premier League": "GB",
            "La Liga": "ES",
            "Serie A": "IT",
            "Bundesliga": "DE",
            "Ligue 1": "FR",
            "Austrian Bundesliga": "AT",
            "Belgian Pro League": "BE",
            "Danish Superliga": "DK",
            "A Lyga": "LT",
            "Virsliga": "LV",
            "Eredivisie": "NL",
            "Eliteserien": "NO",
            "Ekstraklasa": "PL",
            "Primeira Liga": "PT",
            "Super Lig": "TR",
            "Scottish Premiership": "GB",
        }

        for league, country_code in expected.items():
            with self.subTest(league=league):
                self.assertEqual(
                    weather.country_code_for(
                        {},
                        {"league": league},
                    ),
                    country_code,
                )

    def test_div_fallback_remains_available(self):
        self.assertEqual(
            weather.country_code_for(
                {"div": "I1"},
                {},
            ),
            "IT",
        )


if __name__ == "__main__":
    unittest.main()
