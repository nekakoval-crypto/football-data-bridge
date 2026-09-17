import json
import unittest
from pathlib import Path

from scripts.stage85_team_style_dimensions_readiness import (
    build_readiness_report,
)


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "config" / "pbk_team_style_dimensions_v1.json"


class Stage85TeamStyleDimensionsReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with SPEC.open("r", encoding="utf-8") as handle:
            cls.spec = json.load(handle)

    def test_current_spec_has_expected_readiness_counts(self):
        report = build_readiness_report(self.spec)

        self.assertEqual(
            report["counts"],
            {
                "READY_FOR_VALIDATION": 3,
                "PARTIAL": 2,
                "DATA_BLOCKED": 6,
            },
        )

    def test_attack_volume_is_ready_for_validation(self):
        report = build_readiness_report(self.spec)

        rows = {
            row["dimension"]: row
            for row in report["dimensions"]
        }

        attack = rows["ATTACK_VOLUME"]

        self.assertEqual(
            attack["readiness"],
            "READY_FOR_VALIDATION",
        )
        self.assertFalse(attack["style_score_created"])
        self.assertFalse(attack["arbitrary_weights_used"])

    def test_missing_metrics_can_reduce_candidate_to_partial(self):
        report = build_readiness_report(
            self.spec,
            available_metrics={"shots_for"},
        )

        rows = {
            row["dimension"]: row
            for row in report["dimensions"]
        }

        attack = rows["ATTACK_VOLUME"]

        self.assertEqual(
            attack["readiness"],
            "PARTIAL",
        )
        self.assertEqual(
            attack["available_components"],
            ["shots_for"],
        )

    def test_data_blocked_dimension_stays_blocked(self):
        report = build_readiness_report(
            self.spec,
            available_metrics={
                "ppda",
                "high_turnovers",
            },
        )

        rows = {
            row["dimension"]: row
            for row in report["dimensions"]
        }

        pressing = rows["PRESS_INTENSITY"]

        self.assertEqual(
            pressing["declared_status"],
            "DATA_BLOCKED",
        )
        self.assertEqual(
            pressing["readiness"],
            "DATA_BLOCKED",
        )

    def test_readiness_never_creates_style_score_or_signal(self):
        report = build_readiness_report(self.spec)

        self.assertFalse(report["style_score_created"])
        self.assertFalse(report["creates_signal"])
        self.assertFalse(report["probability_mutation"])
        self.assertFalse(report["stake_changes"])
        self.assertFalse(report["r1_r2_r3_mutation"])
        self.assertFalse(report["ui_changes"])
        self.assertFalse(report["api_changes"])


if __name__ == "__main__":
    unittest.main()