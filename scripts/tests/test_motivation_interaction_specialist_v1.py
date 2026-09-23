import unittest

from scripts import motivation_interaction_specialist_v1 as m


class MotivationInteractionSpecialistV1Tests(
    unittest.TestCase
):
    def test_holdout_disjoint(self):
        self.assertTrue(
            set(m.DEV_SEASONS).isdisjoint(
                m.OBSERVED_V1_HOLDOUT
            )
        )

    def test_preregistered_interactions_frozen(self):
        self.assertEqual(
            m.INTERACTIONS,
            (
                "HIGH_PRESSURE_X_FORM_ALIGNMENT",
                "HIGH_PRESSURE_X_SHORT_REST_DISADVANTAGE",
                "HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE",
                "LATE_SURVIVAL_X_SHORT_REST",
            ),
        )

    def test_unknown_is_not_zero(self):
        self.assertIsNone(
            m.side_value("UNKNOWN")
        )
        self.assertIsNone(
            m.form_advantage_side("UNKNOWN")
        )
        self.assertIsNone(
            m.short_rest_disadvantage_side(
                "UNKNOWN"
            )
        )
        self.assertIsNone(
            m.large_rank_disadvantage_side(
                "UNKNOWN"
            )
        )

    def test_alignment_is_directional(self):
        self.assertEqual(
            m.aligned_side(1.0, 1.0),
            1.0,
        )
        self.assertEqual(
            m.aligned_side(-1.0, -1.0),
            -1.0,
        )
        self.assertEqual(
            m.aligned_side(1.0, -1.0),
            0.0,
        )
        self.assertIsNone(
            m.aligned_side(None, 1.0)
        )

    def test_rank_disadvantage_direction(self):
        self.assertEqual(
            m.large_rank_disadvantage_side(
                "HOME_5PLUS_BETTER"
            ),
            -1.0,
        )
        self.assertEqual(
            m.large_rank_disadvantage_side(
                "AWAY_5PLUS_BETTER"
            ),
            1.0,
        )

    def test_active_row_counter(self):
        rows = [
            {"features": [1.0]},
            {"features": [0.0]},
            {"features": [-1.0]},
        ]

        self.assertEqual(
            m.active_rows(rows),
            2,
        )


if __name__ == "__main__":
    unittest.main()
