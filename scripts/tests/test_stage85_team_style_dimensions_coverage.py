import json
import unittest
from pathlib import Path

from scripts.stage85_team_style_dimensions_coverage import (
    build_coverage_report,
)


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "config" / "pbk_team_style_dimensions_v1.json"


class Stage85TeamStyleDimensionsCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with SPEC.open("r", encoding="utf-8") as handle:
            cls.spec = json.load(handle)

    def test_empty_observations_wait_for_live_coverage(self):
        report = build_coverage_report(
            self.spec,
            [],
        )

        self.assertEqual(
            report["status"],
            "WAITING_FOR_STAGE84_OBSERVATIONS",
        )
        self.assertEqual(report["observation_rows"], 0)
        self.assertEqual(report["distinct_profiles"], 0)

        rows = {
            row["dimension"]: row
            for row in report["dimensions"]
        }

        self.assertEqual(
            rows["ATTACK_VOLUME"]["coverage_state"],
            "WAITING_FOR_LIVE_COVERAGE",
        )
        self.assertFalse(
            rows["ATTACK_VOLUME"]["validation_sample_ready"]
        )

    def test_profile_is_eligible_when_minimum_components_are_known(self):
        observations = [
            {
                "league_id": "140",
                "season": "2026",
                "team_id": "77",
                "split": "overall",
                "window": 5,
                "profile_before_utc": "2026-09-01T00:00:00+00:00",
                "metric": "shots_for",
                "metric_status": "KNOWN",
                "value": 12.0,
            },
            {
                "league_id": "140",
                "season": "2026",
                "team_id": "77",
                "split": "overall",
                "window": 5,
                "profile_before_utc": "2026-09-01T00:00:00+00:00",
                "metric": "sot_for",
                "metric_status": "KNOWN",
                "value": 4.0,
            },
        ]

        report = build_coverage_report(
            self.spec,
            observations,
        )

        rows = {
            row["dimension"]: row
            for row in report["dimensions"]
        }

        attack = rows["ATTACK_VOLUME"]

        self.assertEqual(
            attack["coverage_state"],
            "LIVE_COVERAGE_PRESENT",
        )
        self.assertEqual(attack["total_profiles"], 1)
        self.assertEqual(attack["eligible_profiles"], 1)
        self.assertEqual(attack["eligible_ratio"], 1.0)
        self.assertFalse(attack["validation_sample_ready"])

    def test_unknown_metric_is_not_counted_as_known(self):
        observations = [
            {
                "league_id": "140",
                "season": "2026",
                "team_id": "77",
                "split": "overall",
                "window": 5,
                "profile_before_utc": "2026-09-01T00:00:00+00:00",
                "metric": "shots_for",
                "metric_status": "KNOWN",
                "value": 12.0,
            },
            {
                "league_id": "140",
                "season": "2026",
                "team_id": "77",
                "split": "overall",
                "window": 5,
                "profile_before_utc": "2026-09-01T00:00:00+00:00",
                "metric": "sot_for",
                "metric_status": "UNKNOWN",
                "value": None,
            },
        ]

        report = build_coverage_report(
            self.spec,
            observations,
        )

        rows = {
            row["dimension"]: row
            for row in report["dimensions"]
        }

        attack = rows["ATTACK_VOLUME"]

        self.assertEqual(
            attack["coverage_state"],
            "NO_ELIGIBLE_PROFILES",
        )
        self.assertEqual(attack["eligible_profiles"], 0)

    def test_data_blocked_dimension_stays_blocked(self):
        report = build_coverage_report(
            self.spec,
            [],
        )

        rows = {
            row["dimension"]: row
            for row in report["dimensions"]
        }

        pressing = rows["PRESS_INTENSITY"]

        self.assertEqual(
            pressing["coverage_state"],
            "DATA_BLOCKED",
        )
        self.assertFalse(
            pressing["validation_sample_ready"]
        )

    def test_coverage_audit_never_creates_score_or_signal(self):
        report = build_coverage_report(
            self.spec,
            [],
        )

        self.assertFalse(report["style_score_created"])
        self.assertFalse(report["creates_signal"])
        self.assertFalse(report["probability_mutation"])
        self.assertFalse(report["stake_changes"])
        self.assertFalse(report["r1_r2_r3_mutation"])
        self.assertFalse(report["ui_changes"])
        self.assertFalse(report["api_changes"])


if __name__ == "__main__":
    unittest.main()