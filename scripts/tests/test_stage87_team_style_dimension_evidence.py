import unittest

from scripts.stage87_team_style_dimension_evidence import (
    build_dimension_evidence,
)


class Stage87TeamStyleDimensionEvidenceTests(unittest.TestCase):

    def normalized_row(
        self,
        *,
        metric,
        percentile=0.70,
        z_score=0.80,
        status="NORMALIZED",
    ):
        return {
            "league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "team_id": "1",
            "split": "overall",
            "window": 5,
            "metric": metric,
            "profile_before_utc": "2026-09-17T10:00:00Z",
            "observed_at_utc": "2026-09-17T10:01:00Z",
            "normalization_status": status,
            "raw_value": 10.0,
            "population_n": 40,
            "percentile": percentile,
            "z_score": z_score,
        }

    def attack_volume_dimension(self):
        return {
            "id": "ATTACK_VOLUME",
            "status": "CANDIDATE",
            "minimum_known_components": 2,
            "components": [
                {"metric": "shots_for", "direction": "HIGHER_MORE"},
                {"metric": "sot_for", "direction": "HIGHER_MORE"},
                {
                    "metric": "xg_for",
                    "direction": "HIGHER_MORE",
                    "availability": "OPTIONAL_IF_KNOWN",
                },
                {"metric": "corners_for", "direction": "HIGHER_MORE"},
            ],
        }

    def test_two_known_components_ready_for_validation(self):
        rows = [
            self.normalized_row(metric="shots_for"),
            self.normalized_row(metric="sot_for"),
        ]

        result = build_dimension_evidence(
            rows,
            [self.attack_volume_dimension()],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["dimension_status"],
            "READY_FOR_VALIDATION",
        )
        self.assertEqual(result[0]["known_components"], 2)

    def test_less_than_minimum_is_insufficient(self):
        rows = [
            self.normalized_row(metric="shots_for"),
        ]

        result = build_dimension_evidence(
            rows,
            [self.attack_volume_dimension()],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["dimension_status"],
            "INSUFFICIENT_NORMALIZED_COMPONENTS",
        )
        self.assertEqual(result[0]["known_components"], 1)

    def test_dimension_value_is_never_created(self):
        rows = [
            self.normalized_row(metric="shots_for"),
            self.normalized_row(metric="sot_for"),
            self.normalized_row(metric="corners_for"),
        ]

        result = build_dimension_evidence(
            rows,
            [self.attack_volume_dimension()],
        )

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["dimension_value"])
        self.assertFalse(result[0]["aggregation_performed"])
        self.assertFalse(result[0]["arbitrary_weights_used"])


if __name__ == "__main__":
    unittest.main()
