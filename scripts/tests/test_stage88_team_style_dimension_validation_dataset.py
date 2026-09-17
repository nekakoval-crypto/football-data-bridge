import unittest

from scripts.stage88_team_style_dimension_validation_dataset import (
    select_forward_candidates,
    validation_row,
)


class Stage88TeamStyleDimensionValidationTests(unittest.TestCase):

    def ready_row(
        self,
        *,
        profile_before_utc="2026-09-17T10:00:00Z",
        dimension="ATTACK_VOLUME",
    ):
        return {
            "league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "team_id": "1",
            "split": "overall",
            "window": 5,
            "dimension": dimension,
            "dimension_status": "READY_FOR_VALIDATION",
            "profile_before_utc": profile_before_utc,
            "observed_at_utc": profile_before_utc,
            "known_components": 2,
            "minimum_known_components": 2,
            "components": [
                {
                    "metric": "shots_for",
                    "direction": "HIGHER_MORE",
                    "availability": "REQUIRED",
                    "known": True,
                    "normalization_status": "NORMALIZED",
                    "raw_value": 12.0,
                    "population_n": 40,
                    "percentile": 0.70,
                    "z_score": 0.80,
                },
                {
                    "metric": "sot_for",
                    "direction": "HIGHER_MORE",
                    "availability": "REQUIRED",
                    "known": True,
                    "normalization_status": "NORMALIZED",
                    "raw_value": 5.0,
                    "population_n": 40,
                    "percentile": 0.75,
                    "z_score": 0.90,
                },
            ],
            "dimension_value": None,
            "aggregation_performed": False,
        }

    def test_first_seen_series_bootstraps_latest_only(self):
        source = [
            self.ready_row(
                profile_before_utc="2026-09-15T10:00:00Z"
            ),
            self.ready_row(
                profile_before_utc="2026-09-16T10:00:00Z"
            ),
            self.ready_row(
                profile_before_utc="2026-09-17T10:00:00Z"
            ),
        ]

        result = select_forward_candidates(source, [])

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["profile_before_utc"],
            "2026-09-17T10:00:00Z",
        )

    def test_existing_series_accepts_only_newer(self):
        existing = [
            self.ready_row(
                profile_before_utc="2026-09-16T10:00:00Z"
            )
        ]

        source = [
            self.ready_row(
                profile_before_utc="2026-09-15T10:00:00Z"
            ),
            self.ready_row(
                profile_before_utc="2026-09-16T10:00:00Z"
            ),
            self.ready_row(
                profile_before_utc="2026-09-17T10:00:00Z"
            ),
        ]

        result = select_forward_candidates(source, existing)

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["profile_before_utc"],
            "2026-09-17T10:00:00Z",
        )

    def test_validation_row_never_creates_dimension_value(self):
        result = validation_row(self.ready_row())

        self.assertIsNone(result["dimension_value"])
        self.assertIsNone(result["validation_result"])
        self.assertEqual(
            result["validation_status"],
            "UNLABELED_FORWARD_OBSERVATION",
        )
        self.assertFalse(result["aggregation_performed"])
        self.assertFalse(result["arbitrary_weights_used"])
        self.assertFalse(result["zero_to_ten_score"])


if __name__ == "__main__":
    unittest.main()
