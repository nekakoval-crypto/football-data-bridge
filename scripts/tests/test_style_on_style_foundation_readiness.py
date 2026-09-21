import unittest

from scripts.style_on_style_foundation_readiness import build_readiness


class StyleOnStyleFoundationReadinessTests(unittest.TestCase):
    def test_foundation_complete_without_predictive_authority(self):
        payload = build_readiness({
            "stage82": {"evidence_rows_built": 100},
            "stage83": {"profiles_written": 20},
            "stage84": {"rows_written": 500},
            "stage87": {"ready_for_validation": 30},
            "stage88": {"total_validation_rows": 10},
            "stage89": {"total_labels": 2},
            "stage93": {"ready_groups": 0},
            "stage95": {"status": "DATA_BLOCKED"},
        })
        self.assertEqual(payload["checklist_item_12_data_engineering_foundation"], "COMPLETE")
        self.assertEqual(payload["checklist_item_12_predictive_authority"], "NOT_AUTHORIZED")
        self.assertFalse(payload["operational_betting_authority"])

    def test_zero_ready_dimensions_keeps_foundation_open(self):
        payload = build_readiness({
            "stage82": {"evidence_rows_built": 100},
            "stage83": {"profiles_written": 20},
            "stage84": {"rows_written": 500},
            "stage87": {"ready_for_validation": 0},
            "stage88": {"total_validation_rows": 0},
        })
        self.assertEqual(payload["checklist_item_12_data_engineering_foundation"], "IN_PROGRESS")
        self.assertIn(
            "NO_STYLE_DIMENSION_READY_FOR_VALIDATION",
            payload["hard_blockers_to_predictive_authority"],
        )


if __name__ == "__main__":
    unittest.main()
