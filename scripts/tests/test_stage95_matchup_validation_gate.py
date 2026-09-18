import unittest

from scripts.stage95_matchup_validation_gate import (
    build_gate,
)


class Stage95MatchupValidationGateTests(
    unittest.TestCase
):

    def payload(
        self,
        dimensions,
        *,
        threshold_policy=False,
    ):
        return {
            "version": (
                "PBK_STAGE94_STYLE_DIMENSION_VALIDATION_STATISTICS_V1"
            ),
            "validation_threshold_policy_defined": (
                threshold_policy
            ),
            "groups": [
                {
                    "dimension": dimension,
                    "validation_status": (
                        "VALIDATION_EVIDENCE_AVAILABLE"
                    ),
                }
                for dimension in dimensions
            ],
        }

    def test_current_operational_dimensions_do_not_authorize_matchup(self):
        gate = build_gate(
            self.payload(
                {
                    "ATTACK_VOLUME",
                    "POSSESSION_CONTROL",
                    "DEFENSIVE_RESISTANCE",
                }
            )
        )

        self.assertEqual(
            gate["status"],
            "DATA_BLOCKED",
        )
        self.assertEqual(
            gate["components_with_required_evidence"],
            0,
        )
        self.assertFalse(
            gate["matchup_grade_authorized"]
        )
        self.assertFalse(
            gate["validated_matchup_claim_allowed"]
        )

    def test_exact_component_dimensions_only_make_evidence_available(self):
        gate = build_gate(
            self.payload(
                {
                    "PRESS_INTENSITY",
                    "BUILDUP_RESISTANCE",
                }
            )
        )

        component = gate["components"][
            "PRESS_VS_BUILDUP"
        ]

        self.assertEqual(
            component["status"],
            "VALIDATION_POLICY_PENDING",
        )
        self.assertFalse(
            component[
                "matchup_effect_claim_authorized"
            ]
        )
        self.assertFalse(
            gate["matchup_grade_authorized"]
        )

    def test_even_defined_policy_does_not_auto_authorize_grade(self):
        gate = build_gate(
            self.payload(
                {
                    "PRESS_INTENSITY",
                    "BUILDUP_RESISTANCE",
                },
                threshold_policy=True,
            )
        )

        component = gate["components"][
            "PRESS_VS_BUILDUP"
        ]

        self.assertEqual(
            component["status"],
            "EVIDENCE_AVAILABLE_NOT_AUTHORIZED",
        )
        self.assertFalse(
            gate["overall_edge_authorized"]
        )
        self.assertFalse(
            gate["winner_claim_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
