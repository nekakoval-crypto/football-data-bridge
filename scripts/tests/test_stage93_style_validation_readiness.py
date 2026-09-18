import unittest

from scripts.stage93_style_validation_readiness import (
    build_readiness,
)


class Stage93StyleValidationReadinessTests(unittest.TestCase):

    def observation(
        self,
        *,
        team_id,
        profile_before_utc,
        dimension="ATTACK_VOLUME",
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
            "dimension": dimension,
            "profile_before_utc": profile_before_utc,
            "dimension_value": None,
            "validation_status": (
                "UNLABELED_FORWARD_OBSERVATION"
            ),
            "aggregation_performed": False,
        }

    def label(
        self,
        observation,
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
        }

    def sample(
        self,
        n,
    ):
        observations = []
        labels = []

        for index in range(n):
            row = self.observation(
                team_id=(index % 20) + 1,
                profile_before_utc=(
                    f"2026-09-{(index % 9) + 10:02d}"
                    f"T{index % 24:02d}:00:00Z"
                ),
            )

            observations.append(row)
            labels.append(self.label(row))

        return observations, labels

    def test_no_forward_labels_is_not_ready(self):
        observations, _ = self.sample(5)

        rows = build_readiness(
            observations,
            [],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["forward_observation_n"],
            5,
        )
        self.assertEqual(
            rows[0]["forward_labeled_sample_n"],
            0,
        )
        self.assertEqual(
            rows[0]["readiness_status"],
            "NO_LABELED_SAMPLES",
        )

    def test_twenty_nine_labeled_samples_is_insufficient(self):
        observations, labels = self.sample(29)

        rows = build_readiness(
            observations,
            labels,
        )

        self.assertEqual(
            rows[0]["forward_labeled_sample_n"],
            29,
        )
        self.assertEqual(
            rows[0]["readiness_status"],
            "INSUFFICIENT_DATA",
        )

    def test_thirty_labeled_samples_is_ready(self):
        observations, labels = self.sample(30)

        rows = build_readiness(
            observations,
            labels,
        )

        self.assertEqual(
            rows[0]["forward_labeled_sample_n"],
            30,
        )
        self.assertEqual(
            rows[0]["minimum_labeled_samples"],
            30,
        )
        self.assertEqual(
            rows[0]["readiness_status"],
            "READY",
        )

    def test_duplicate_observation_does_not_inflate_sample(self):
        observations, labels = self.sample(1)

        observations.append(
            dict(observations[0])
        )
        labels.append(
            dict(labels[0])
        )

        rows = build_readiness(
            observations,
            labels,
            minimum_samples=2,
        )

        self.assertEqual(
            rows[0]["forward_observation_n"],
            1,
        )
        self.assertEqual(
            rows[0]["forward_labeled_sample_n"],
            1,
        )
        self.assertEqual(
            rows[0]["readiness_status"],
            "INSUFFICIENT_DATA",
        )


if __name__ == "__main__":
    unittest.main()
