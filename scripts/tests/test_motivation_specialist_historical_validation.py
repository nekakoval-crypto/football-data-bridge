import unittest

from scripts import motivation_specialist_historical_validation as model


class MotivationSpecialistHistoricalValidationTests(
    unittest.TestCase
):
    def test_probability_vector_sums_to_one(self):
        result = model.challenger_probabilities(
            (0.50, 0.28, 0.22),
            [1, 0, 0, 0, 0, 0],
            [0.2, 0, 0, 0, 0, 0],
        )

        self.assertAlmostEqual(
            sum(result),
            1.0,
            places=14,
        )

        self.assertGreater(
            result[0],
            0.50,
        )

        self.assertLess(
            result[2],
            0.22,
        )

    def test_unknown_feature_is_not_zero(self):
        row = {
            "full_table_available": "false",
        }

        self.assertIsNone(
            model.feature_vector(row)
        )

    def test_side_encoding_is_directional(self):
        self.assertEqual(
            model.side_value("HOME_ONLY"),
            1.0,
        )

        self.assertEqual(
            model.side_value("AWAY_ONLY"),
            -1.0,
        )

        self.assertEqual(
            model.side_value("BOTH"),
            0.0,
        )

        self.assertIsNone(
            model.side_value("UNKNOWN")
        )

    def test_fit_learns_direction_on_synthetic_sample(self):
        rows = []

        for index in range(300):
            home = index % 2 == 0

            rows.append({
                "historical_match_id": str(index),
                "season": "S",
                "league": "L",
                "market": (
                    0.40,
                    0.30,
                    0.30,
                ),
                "features": [
                    1.0 if home else -1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ],
                "outcome": (
                    "H"
                    if home
                    else "A"
                ),
            })

        beta = model.fit(rows)

        self.assertGreater(
            beta[0],
            0.0,
        )

        baseline = model.evaluate(
            rows,
            [0.0] * len(model.FEATURES),
        )

        challenger = model.evaluate(
            rows,
            beta,
        )

        self.assertLess(
            challenger["challenger_logloss"],
            baseline["challenger_logloss"],
        )

    def test_season_split_is_frozen_four_plus_three_closing_market(self):
        rows = []

        for season in range(2019, 2026):
            rows.append({
                "season": str(season),
            })

        (
            train_seasons,
            holdout_seasons,
            train,
            holdout,
        ) = model.season_split(rows)

        self.assertEqual(
            train_seasons,
            [
                "2019",
                "2020",
                "2021",
                "2022",
            ],
        )

        self.assertEqual(
            holdout_seasons,
            [
                "2023",
                "2024",
                "2025",
            ],
        )

        self.assertEqual(len(train), 4)
        self.assertEqual(len(holdout), 3)

    def test_no_generic_intercept_is_part_of_model(self):
        self.assertEqual(
            len(model.FEATURES),
            6,
        )

        self.assertNotIn(
            "INTERCEPT",
            model.FEATURES,
        )


if __name__ == "__main__":
    unittest.main()
