import copy
import json
import unittest
from pathlib import Path

from scripts.validate_grade_readiness import REQUIRED_IDS, validate


class GradeReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(Path("config/pbk_grade_readiness.json").read_text(encoding="utf-8"))

    def test_registry_is_valid(self):
        self.assertEqual(validate(copy.deepcopy(self.payload)), [])

    def test_required_metrics_are_present(self):
        ids = {row["id"] for row in self.payload["metrics"]}
        self.assertTrue(REQUIRED_IDS.issubset(ids))

    def test_overall_grade_does_not_hide_proxies(self):
        row = next(row for row in self.payload["metrics"] if row["id"] == "PLAYER_OVERALL_GRADE")
        self.assertEqual(row["components"]["progression"], "PROXY_LIMITED")
        self.assertEqual(row["components"]["pressing"], "UNAVAILABLE_IN_AGGREGATE_SOURCE")

    def test_empty_player_evidence_is_not_called_validated(self):
        for metric_id in ("PLAYER_OVERALL_GRADE", "PLAYER_FORM_GRADE", "XI_QUALITY", "PLAYER_IMPORTANCE"):
            row = next(row for row in self.payload["metrics"] if row["id"] == metric_id)
            self.assertIn(row["status"], {"DATA_BLOCKED", "VALIDATION_PENDING", "PROXY_LIMITED"})

    def test_availability_foundations_are_code_ready_but_not_promoted(self):
        for metric_id in ("ABSENCE_IMPACT", "RETURN_IMPACT", "ROTATION_QUALITY_IMPACT"):
            row = next(row for row in self.payload["metrics"] if row["id"] == metric_id)
            self.assertTrue(row["code_ready"])
            self.assertIn(row["status"], {"DATA_BLOCKED", "VALIDATION_PENDING", "PROXY_LIMITED"})

    def test_absence_and_return_scores_remain_unauthorized(self):
        absence = next(row for row in self.payload["metrics"] if row["id"] == "ABSENCE_IMPACT")
        returned = next(row for row in self.payload["metrics"] if row["id"] == "RETURN_IMPACT")
        self.assertEqual(absence["components"]["total_impact"], "FORBIDDEN_UNTIL_WEIGHTING_VALIDATED")
        self.assertEqual(returned["components"]["return_impact_score"], "NOT_AUTHORIZED")

    def test_matchup_foundation_is_code_ready_but_not_promoted(self):
        row = next(row for row in self.payload["metrics"] if row["id"] == "MATCHUP_GRADE")
        self.assertTrue(row["code_ready"])
        self.assertIn(row["status"], {"DATA_BLOCKED", "VALIDATION_PENDING", "PROXY_LIMITED"})
        self.assertEqual(row["components"]["formation"], "CONTEXT_ONLY_NOT_STYLE")
        self.assertEqual(row["components"]["overall_matchup_grade"], "NOT_AUTHORIZED")

    def test_not_implemented_metrics_do_not_claim_code_ready(self):
        for row in self.payload["metrics"]:
            if row["status"] == "NOT_IMPLEMENTED":
                self.assertFalse(row["code_ready"])

    def test_validated_requires_evidence(self):
        payload = copy.deepcopy(self.payload)
        payload["metrics"][0]["status"] = "VALIDATED"
        errors = validate(payload)
        self.assertTrue(any("validation_evidence" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
