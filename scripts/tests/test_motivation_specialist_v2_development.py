import unittest

from scripts import motivation_specialist_v2_development as v2


class MotivationSpecialistV2DevelopmentTests(
    unittest.TestCase
):
    def test_v1_holdout_is_explicitly_outside_development(self):
        self.assertEqual(
            v2.DEV_SEASONS,
            (
                "2019/2020",
                "2020/2021",
                "2021/2022",
                "2022/2023",
            ),
        )

        self.assertEqual(
            v2.V1_OBSERVED_HOLDOUT,
            (
                "2023/2024",
                "2024/2025",
                "2025/2026",
            ),
        )

        self.assertTrue(
            set(v2.DEV_SEASONS).isdisjoint(
                v2.V1_OBSERVED_HOLDOUT
            )
        )

    def test_expanding_folds_are_temporal(self):
        self.assertEqual(
            v2.FOLDS[0]["train"],
            (
                "2019/2020",
                "2020/2021",
            ),
        )

        self.assertEqual(
            v2.FOLDS[0]["test"],
            "2021/2022",
        )

        self.assertEqual(
            v2.FOLDS[1]["train"],
            (
                "2019/2020",
                "2020/2021",
                "2021/2022",
            ),
        )

        self.assertEqual(
            v2.FOLDS[1]["test"],
            "2022/2023",
        )

    def test_sign_guard(self):
        self.assertEqual(
            v2.sign(0.2),
            "POSITIVE",
        )
        self.assertEqual(
            v2.sign(-0.2),
            "NEGATIVE",
        )
        self.assertEqual(
            v2.sign(0.0),
            "ZERO",
        )

    def test_single_feature_fit_learns_direction(self):
        rows = []

        for index in range(300):
            home = index % 2 == 0

            rows.append({
                "market": (
                    0.40,
                    0.30,
                    0.30,
                ),
                "features": [
                    1.0
                    if home
                    else -1.0
                ],
                "outcome": (
                    "H"
                    if home
                    else "A"
                ),
            })

        beta = v2.fit_single(rows)

        self.assertGreater(
            beta,
            0.0,
        )

    def test_selection_requires_all_guards(self):
        rows = []

        # Synthetic chronology where one directional feature
        # is deliberately predictive in both development folds.
        seasons = [
            "2019/2020",
            "2020/2021",
            "2021/2022",
            "2022/2023",
        ]

        fixture = 0

        for season in seasons:
            for index in range(1400):
                fixture += 1
                home = index % 2 == 0

                rows.append({
                    "historical_match_id": str(
                        fixture
                    ),
                    "season": season,
                    "league": "TEST",
                    "market": (
                        0.40,
                        0.30,
                        0.30,
                    ),
                    "features": [
                        1.0
                        if home
                        else -1.0
                    ]
                    + [0.0] * (
                        len(v2.FEATURES) - 1
                    ),
                    "outcome": (
                        "H"
                        if home
                        else "A"
                    ),
                })

        result = v2.develop_feature(
            rows,
            0,
            v2.FEATURES[0],
        )

        self.assertTrue(
            result[
                "sample_ready_all_folds"
            ]
        )
        self.assertTrue(
            result[
                "coefficient_sign_stable"
            ]
        )
        self.assertTrue(
            result[
                "brier_improved_all_folds"
            ]
        )
        self.assertTrue(
            result[
                "logloss_improved_all_folds"
            ]
        )
        self.assertTrue(
            result[
                "selected_for_frozen_v2"
            ]
        )


if __name__ == "__main__":
    unittest.main()
