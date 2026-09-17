from __future__ import annotations

import unittest

from scripts.stage84_team_style_metric_normalization import (
    MIN_POPULATION,
    PopulationKey,
    build_population,
    empirical_percentile,
    normalize_against_population,
    normalize_metric,
    validate_population_scope,
    z_score,
)


class Stage84MetricNormalizationTests(unittest.TestCase):
    def test_empirical_percentile_uses_midrank(self):
        values = [1, 2, 3, 4]

        self.assertEqual(empirical_percentile(values, 1), 12.5)
        self.assertEqual(empirical_percentile(values, 2), 37.5)
        self.assertEqual(empirical_percentile(values, 4), 87.5)

    def test_z_score_is_standardized_against_population(self):
        values = [10, 20, 30, 40]

        result = z_score(values, 25)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 0.0, places=6)

    def test_constant_population_has_zero_z_for_equal_target(self):
        values = [5.0] * 30

        self.assertEqual(z_score(values, 5.0), 0.0)
        self.assertIsNone(z_score(values, 6.0))

    def test_unknown_raw_value_is_not_zero_filled(self):
        result = normalize_metric(
            raw_value=None,
            population_values=range(40),
        )

        self.assertEqual(result["status"], "UNKNOWN_RAW_VALUE")
        self.assertIsNone(result["raw_value"])
        self.assertIsNone(result["percentile"])
        self.assertIsNone(result["z_score"])
        self.assertIsNone(result["style_dimension_value"])

    def test_insufficient_population_does_not_normalize(self):
        result = normalize_metric(
            raw_value=15,
            population_values=range(MIN_POPULATION - 1),
        )

        self.assertEqual(result["status"], "INSUFFICIENT_POPULATION")
        self.assertEqual(result["population_n"], MIN_POPULATION - 1)
        self.assertIsNone(result["percentile"])
        self.assertIsNone(result["z_score"])
        self.assertIsNone(result["style_dimension_value"])

    def test_valid_population_normalizes_without_style_dimension(self):
        result = normalize_metric(
            raw_value=15,
            population_values=range(40),
        )

        self.assertEqual(result["status"], "NORMALIZED")
        self.assertEqual(result["population_n"], 40)
        self.assertIsNotNone(result["percentile"])
        self.assertIsNotNone(result["z_score"])
        self.assertIsNone(result["style_dimension_value"])

    def test_scope_rejects_post_cutoff_observation(self):
        row = {
            "observed_at_utc": "2026-09-18T12:00:00+00:00",
            "profile_before_utc": "2026-09-17T12:00:00+00:00",
        }

        valid, reason = validate_population_scope(
            row,
            before_utc="2026-09-17T13:00:00+00:00",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "OBSERVED_AFTER_CUTOFF")

    def test_scope_rejects_profile_built_after_cutoff(self):
        row = {
            "observed_at_utc": "2026-09-17T10:00:00+00:00",
            "profile_before_utc": "2026-09-18T12:00:00+00:00",
        }

        valid, reason = validate_population_scope(
            row,
            before_utc="2026-09-17T13:00:00+00:00",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "PROFILE_AFTER_CUTOFF")

    def test_build_population_keeps_exact_scope_only(self):
        key = PopulationKey(
            league_id="140",
            season="2026",
            split="overall",
            window=10,
            metric="shots_for",
        )

        rows = [
            {
                "league_id": "140",
                "season": "2026",
                "split": "overall",
                "window": 10,
                "metric": "shots_for",
                "value": 12,
                "observed_at_utc": "2026-09-01T10:00:00+00:00",
                "profile_before_utc": "2026-09-01T09:00:00+00:00",
            },
            {
                "league_id": "39",
                "season": "2026",
                "split": "overall",
                "window": 10,
                "metric": "shots_for",
                "value": 99,
                "observed_at_utc": "2026-09-01T10:00:00+00:00",
                "profile_before_utc": "2026-09-01T09:00:00+00:00",
            },
            {
                "league_id": "140",
                "season": "2026",
                "split": "home",
                "window": 10,
                "metric": "shots_for",
                "value": 88,
                "observed_at_utc": "2026-09-01T10:00:00+00:00",
                "profile_before_utc": "2026-09-01T09:00:00+00:00",
            },
            {
                "league_id": "140",
                "season": "2026",
                "split": "overall",
                "window": 5,
                "metric": "shots_for",
                "value": 77,
                "observed_at_utc": "2026-09-01T10:00:00+00:00",
                "profile_before_utc": "2026-09-01T09:00:00+00:00",
            },
            {
                "league_id": "140",
                "season": "2026",
                "split": "overall",
                "window": 10,
                "metric": "xg_for",
                "value": 66,
                "observed_at_utc": "2026-09-01T10:00:00+00:00",
                "profile_before_utc": "2026-09-01T09:00:00+00:00",
            },
        ]

        values, exclusions = build_population(
            rows,
            key=key,
            before_utc="2026-09-02T00:00:00+00:00",
        )

        self.assertEqual(values, [12.0])
        self.assertEqual(exclusions["wrong_league"], 1)
        self.assertEqual(exclusions["wrong_split"], 1)
        self.assertEqual(exclusions["wrong_window"], 1)
        self.assertEqual(exclusions["wrong_metric"], 1)

    def test_normalize_against_population_never_broadens_scope(self):
        target = {
            "league_id": "140",
            "season": "2026",
            "split": "overall",
            "window": 10,
            "metric": "shots_for",
            "value": 15,
            "observed_at_utc": "2026-09-15T10:00:00+00:00",
            "profile_before_utc": "2026-09-15T09:00:00+00:00",
        }

        population = []
        for idx in range(29):
            population.append(
                {
                    "league_id": "140",
                    "season": "2026",
                    "split": "overall",
                    "window": 10,
                    "metric": "shots_for",
                    "value": idx,
                    "observed_at_utc": "2026-09-14T10:00:00+00:00",
                    "profile_before_utc": "2026-09-14T09:00:00+00:00",
                }
            )

        for idx in range(100):
            population.append(
                {
                    "league_id": "39",
                    "season": "2026",
                    "split": "overall",
                    "window": 10,
                    "metric": "shots_for",
                    "value": idx,
                    "observed_at_utc": "2026-09-14T10:00:00+00:00",
                    "profile_before_utc": "2026-09-14T09:00:00+00:00",
                }
            )

        result = normalize_against_population(
            target_row=target,
            population_rows=population,
            before_utc="2026-09-16T00:00:00+00:00",
        )

        self.assertEqual(result["status"], "INSUFFICIENT_POPULATION")
        self.assertEqual(result["normalized"]["population_n"], 29)
        self.assertFalse(result["silent_scope_broadening"])
        self.assertIsNone(result["style_dimension_value"])

    def test_invalid_target_scope_is_not_normalized(self):
        target = {
            "league_id": "140",
            "season": "2026",
            "split": "overall",
            "window": 10,
            "metric": "shots_for",
            "value": 15,
            "observed_at_utc": "2026-09-20T10:00:00+00:00",
            "profile_before_utc": "2026-09-15T09:00:00+00:00",
        }

        result = normalize_against_population(
            target_row=target,
            population_rows=[],
            before_utc="2026-09-16T00:00:00+00:00",
        )

        self.assertEqual(result["status"], "INVALID_TARGET_SCOPE")
        self.assertEqual(result["reason"], "OBSERVED_AFTER_CUTOFF")
        self.assertIsNone(result["normalized"])
        self.assertEqual(result["provider_calls_added"], 0)


if __name__ == "__main__":
    unittest.main()
