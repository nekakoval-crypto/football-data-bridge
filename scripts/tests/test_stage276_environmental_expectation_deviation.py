import unittest

from scripts import stage276_environmental_expectation_deviation as m


class EnvironmentalExpectationDeviationTests(unittest.TestCase):

    def market_row(self, **extra):
        row = {
            "historical_match_id": "m1",
            "league_code": "E0",
            "league_name": "Premier League",
            "season_label": "2025/2026",
            "date_iso": "2026-09-20",
            "avg_close_over_25": "1.60",
            "avg_close_under_25": "2.40",
            "avg_close_home": "1.80",
            "avg_close_draw": "3.80",
            "avg_close_away": "4.50",
        }
        row.update(extra)
        return row

    def bridge_row(self):
        return {
            "historical_match_id": "m1",
            "api_fixture_id": "10",
            "provider_league_id": "39",
            "api_kickoff_utc": "2026-09-20T15:00:00Z",
            "mapping_status": "AUTO",
            "one_to_one_verified": "true",
            "fuzzy_string_matching_used": "false",
        }

    def mechanism_row(self, home_goals="1", away_goals="0"):
        return {
            "fixture_id": "10",
            "home_team": "Home",
            "away_team": "Away",
            "home_goals": home_goals,
            "away_goals": away_goals,
            "environment_source_class": "HISTORICAL_FORECAST_ASSIMILATION_PROXY",
            "environment_geocode_quality_status": "VERIFIED_LOCALITY_V4",
            "environment_geocode_resolver_version": "PBK_GEOCODE_V4",
            "temperature_mean_c": "34",
            "relative_humidity_mean_pct": "70",
            "rain_sum_mm": "0",
            "wind_gust_max_kmh": "20",
            "shots_total": "18",
            "shots_on_goal_total": "5",
            "shots_outsidebox_total": "8",
            "goalkeeper_saves_total": "4",
            "corners_total": "7",
            "passes_accuracy_mean": "74",
            "expected_goals_total": "1.3",
        }

    def test_no_vig_total_probability(self):
        pair = m.no_vig_pair("2.0", "2.0")
        self.assertIsNotNone(pair)
        self.assertAlmostEqual(pair[0], 0.5)
        self.assertAlmostEqual(pair[1], 0.5)

    def test_expected_over_actual_under(self):
        rows, diag = m.build_rows(
            [self.market_row()],
            [self.bridge_row()],
            [self.mechanism_row("1", "0")],
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["total_market_expectation_band"], "OVER_LEAN")
        self.assertEqual(row["actual_over25"], "false")
        self.assertEqual(
            row["total_expectation_deviation_class"],
            "EXPECTED_OVER_ACTUAL_UNDER",
        )
        self.assertLess(float(row["over25_residual"]), 0)
        self.assertEqual(diag["joined_expectation_environment_rows"], 1)

    def test_expected_under_actual_over(self):
        market = self.market_row(
            avg_close_over_25="2.50",
            avg_close_under_25="1.55",
        )
        rows, _ = m.build_rows(
            [market],
            [self.bridge_row()],
            [self.mechanism_row("4", "3")],
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["total_market_expectation_band"], "UNDER_LEAN")
        self.assertEqual(row["actual_over25"], "true")
        self.assertEqual(
            row["total_expectation_deviation_class"],
            "EXPECTED_UNDER_ACTUAL_OVER",
        )
        self.assertGreater(float(row["over25_residual"]), 0)

    def test_balanced_is_not_forced_into_high_or_low(self):
        market = self.market_row(
            avg_close_over_25="1.95",
            avg_close_under_25="1.95",
        )
        rows, _ = m.build_rows(
            [market],
            [self.bridge_row()],
            [self.mechanism_row("2", "1")],
        )
        self.assertEqual(
            rows[0]["total_market_expectation_band"],
            "BALANCED",
        )
        self.assertEqual(
            rows[0]["total_expectation_deviation_class"],
            "BALANCED_ACTUAL_OVER",
        )

    def test_unverified_environment_geocode_is_fail_closed(self):
        env=self.mechanism_row()
        env["environment_geocode_quality_status"]=""
        env["environment_geocode_resolver_version"]=""
        rows,diag=m.build_rows(
            [self.market_row()],
            [self.bridge_row()],
            [env],
        )
        self.assertEqual(rows,[])
        self.assertEqual(diag["unverified_environment_geocode"],1)

    def test_review_bridge_is_fail_closed(self):
        bridge = self.bridge_row()
        bridge["mapping_status"] = "REVIEW"
        rows, _ = m.build_rows(
            [self.market_row()],
            [bridge],
            [self.mechanism_row()],
        )
        self.assertEqual(rows, [])

    def test_missing_ou_market_does_not_invent_expectation(self):
        market = self.market_row(
            avg_close_over_25="",
            avg_close_under_25="",
        )
        rows, diag = m.build_rows(
            [market],
            [self.bridge_row()],
            [self.mechanism_row()],
        )
        self.assertEqual(rows, [])
        self.assertEqual(diag["missing_closing_ou25"], 1)

    def test_output_remains_research_only(self):
        rows, _ = m.build_rows(
            [self.market_row()],
            [self.bridge_row()],
            [self.mechanism_row()],
        )
        row = rows[0]
        self.assertEqual(row["expectation_source_is_prematch_market"], "true")
        self.assertEqual(row["environment_source_is_postmatch_proxy"], "true")
        self.assertEqual(row["causal_claim_authorized"], "false")
        self.assertEqual(row["predictive_authority"], "NOT_AUTHORIZED")
        self.assertEqual(row["betting_authority"], "NOT_AUTHORIZED")
        self.assertEqual(row["probability_mutation"], "false")
        self.assertNotIn("expected_goals_market", row)

    def test_meta_freezes_expectation_bins(self):
        meta = m.build_meta([], {})
        self.assertFalse(meta["expected_goals_reverse_engineered"])
        self.assertEqual(
            meta["primary_expectation_baseline"],
            "CLOSING_OU25_NO_VIG_PROBABILITY",
        )
        self.assertIn("0.55", meta["expectation_bands"]["OVER_LEAN"])
        self.assertIn("0.45", meta["expectation_bands"]["UNDER_LEAN"])


if __name__ == "__main__":
    unittest.main()
