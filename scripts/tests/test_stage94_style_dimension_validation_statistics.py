import unittest

from scripts.stage94_style_dimension_validation_statistics import (
    build_statistics,
)


class Stage94StyleDimensionValidationStatisticsTests(
    unittest.TestCase
):

    def observation(
        self,
        *,
        team_id,
        timestamp,
        z_score,
    ):
        return {
            "version": (
                "PBK_STAGE88_STYLE_DIMENSION_VALIDATION_DATASET_V1"
            ),
            "league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "team_id": str(team_id),
            "split": "overall",
            "window": 5,
            "dimension": "ATTACK_VOLUME",
            "profile_before_utc": timestamp,
            "validation_status": (
                "UNLABELED_FORWARD_OBSERVATION"
            ),
            "aggregation_performed": False,
            "components": [
                {
                    "metric": "shots_for",
                    "direction": "HIGHER",
                    "z_score": z_score,
                }
            ],
        }

    def label(
        self,
        observation,
        outcome,
    ):
        return {
            "version": (
                "PBK_STAGE89_STYLE_DIMENSION_FORWARD_LABELS_V1"
            ),
            "league_id": observation["league_id"],
            "season": observation["season"],
            "team_id": observation["team_id"],
            "split": observation["split"],
            "window": observation["window"],
            "dimension": observation["dimension"],
            "profile_before_utc": (
                observation["profile_before_utc"]
            ),
            "label_status": (
                "FORWARD_MATCH_ATTACHED"
            ),
            "forward_outcomes": {
                "shots_for": outcome,
            },
        }

    def readiness(
        self,
        status="READY",
    ):
        return {
            "version": (
                "PBK_STAGE93_STYLE_VALIDATION_READINESS_V1"
            ),
            "groups": [
                {
                    "league_id": "39",
                    "season": "2026",
                    "split": "overall",
                    "window": 5,
                    "dimension": "ATTACK_VOLUME",
                    "readiness_status": status,
                }
            ],
        }

    def sample(self, n):
        observations = []
        labels = []

        for index in range(n):
            row = self.observation(
                team_id=(index % 20) + 1,
                timestamp=(
                    f"2026-09-{(index % 9) + 10:02d}"
                    f"T{index % 24:02d}:"
                    f"{index % 60:02d}:00Z"
                ),
                z_score=float(index),
            )

            observations.append(row)

            labels.append(
                self.label(
                    row,
                    float(index * 2),
                )
            )

        return observations, labels

    def test_not_ready_group_is_excluded(self):
        observations, labels = self.sample(30)

        rows = build_statistics(
            observations,
            labels,
            self.readiness(
                "INSUFFICIENT_DATA"
            ),
        )

        self.assertEqual(rows, [])

    def test_twenty_nine_pairs_remain_insufficient(self):
        observations, labels = self.sample(29)

        rows = build_statistics(
            observations,
            labels,
            self.readiness(),
        )

        component = rows[0]["components"][0]

        self.assertEqual(
            component["paired_sample_n"],
            29,
        )
        self.assertEqual(
            component["validation_status"],
            "INSUFFICIENT_PAIRED_SAMPLES",
        )

    def test_thirty_pairs_produce_validation_evidence(self):
        observations, labels = self.sample(30)

        rows = build_statistics(
            observations,
            labels,
            self.readiness(),
        )

        self.assertEqual(len(rows), 1)

        component = rows[0]["components"][0]

        self.assertEqual(
            component["paired_sample_n"],
            30,
        )
        self.assertEqual(
            component["validation_status"],
            "VALIDATION_EVIDENCE_AVAILABLE",
        )
        self.assertAlmostEqual(
            component["pearson_r"],
            1.0,
        )

        self.assertEqual(
            rows[0]["validation_status"],
            "VALIDATION_EVIDENCE_AVAILABLE",
        )

    def test_duplicate_observation_key_does_not_inflate_pairs(self):
        observations, labels = self.sample(1)

        observations.append(
            dict(observations[0])
        )
        labels.append(
            dict(labels[0])
        )

        rows = build_statistics(
            observations,
            labels,
            self.readiness(),
            minimum_samples=2,
        )

        self.assertEqual(
            rows[0]["components"][0][
                "paired_sample_n"
            ],
            1,
        )

    def test_no_automatic_validation_decision(self):
        observations, labels = self.sample(30)

        rows = build_statistics(
            observations,
            labels,
            self.readiness(),
        )

        self.assertFalse(
            rows[0][
                "automatic_validation_decision"
            ]
        )
        self.assertFalse(
            rows[0][
                "validation_threshold_policy_defined"
            ]
        )


if __name__ == "__main__":
    unittest.main()
