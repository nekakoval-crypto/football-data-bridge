import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import stage272_environmental_forward_monitor as m


class EnvironmentalForwardMonitorTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ops = self.root / "ops"
        self.ops.mkdir()
        self.config = self.root / "config.json"
        cfg = json.loads(
            Path("config/pbk_environmental_stress_v1_forward.json")
            .read_text(encoding="utf-8")
        )
        self.config.write_text(json.dumps(cfg), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def feature(self, rule="R1", captured="2026-09-24T17:00:00Z"):
        return {
            "forward_id": f"{rule}|I1|10",
            "rule": rule,
            "api_fixture_id": "10",
            "kickoff_utc": "2026-09-24T19:00:00Z",
            "home_team": "Home",
            "away_team": "Away",
            "weather_feature_status": "PREMATCH_FROZEN",
            "weather_snapshot_type": "T3",
            "weather_captured_at_utc": captured,
            "weather_evidence_time_status": "PREMATCH_FROZEN",
            "weather_usable_for_prematch": "true",
            "venue_id": "100",
            "venue_name": "Example",
            "surface_provider": "grass",
            "roof_type": "UNKNOWN",
            "roof_state_actual": "UNKNOWN",
            "weather_exposure_resolution": "UNKNOWN",
            "environment_feature_state": "RESEARCH_FEATURES_AVAILABLE",
            "thermal_group_status": "KNOWN",
            "wind_group_status": "KNOWN",
            "precipitation_group_status": "KNOWN",
            "visibility_thunder_group_status": "KNOWN",
            "air_quality_group_status": "CAPTURED",
            "altitude_group_status": "KNOWN",
            "surface_group_status": "KNOWN",
            "venue_environment_status": "UNKNOWN",
            "temperature_c": "20",
            "research_only": "YES",
            "predictive_authority": "NOT_AUTHORIZED",
        }

    def before(self):
        return datetime(2026, 9, 24, 18, 0, tzinfo=timezone.utc)

    def after(self):
        return datetime(2026, 9, 24, 20, 0, tzinfo=timezone.utc)

    def test_contract_is_locked(self):
        cfg = json.loads(self.config.read_text(encoding="utf-8"))
        m.validate_contract(cfg)

    def test_duplicate_rules_count_fixture_once(self):
        added, diag = m.capture_prematch(
            [self.feature("R1"), self.feature("R2")],
            [],
            self.before(),
        )
        self.assertEqual(len(added), 1)
        self.assertEqual(diag["prematch_events_created"], 1)

    def test_missed_fixture_cannot_be_backfilled(self):
        added, diag = m.capture_prematch(
            [self.feature()],
            [],
            self.after(),
        )
        self.assertEqual(added, [])
        self.assertEqual(diag["skipped_after_kickoff_no_backfill"], 1)

    def test_missing_weather_cannot_freeze(self):
        row = self.feature()
        row["weather_feature_status"] = "MISSING"
        added, _ = m.capture_prematch([row], [], self.before())
        self.assertEqual(added, [])

    def test_postmatch_weather_cannot_freeze(self):
        row = self.feature(captured="2026-09-24T20:00:00Z")
        added, _ = m.capture_prematch([row], [], self.before())
        self.assertEqual(added, [])

    def test_exact_ft_settlement_requires_frozen_prematch(self):
        prematch, _ = m.capture_prematch(
            [self.feature()],
            [],
            self.before(),
        )
        overlay = [{
            "fixture_id": "10",
            "source_status": "FT",
            "status": "finished",
            "score_home": "2",
            "score_away": "1",
            "observed_at_utc": "2026-09-24T21:00:00Z",
        }]
        settled, diag = m.settle(overlay, prematch, [])
        self.assertEqual(len(settled), 1)
        self.assertEqual(settled[0]["payload"]["result"], "H")
        self.assertEqual(diag["settlements_created"], 1)

    def test_historical_overlay_cannot_create_prematch(self):
        overlay = [{
            "fixture_id": "10",
            "source_status": "FT",
            "status": "finished",
            "score_home": "2",
            "score_away": "1",
            "observed_at_utc": "2026-09-24T21:00:00Z",
        }]
        settled, _ = m.settle(overlay, [], [])
        self.assertEqual(settled, [])

    def test_report_is_readiness_not_effect_claim(self):
        cfg = json.loads(self.config.read_text(encoding="utf-8"))
        report = m.performance_report(cfg, [], [])
        self.assertEqual(
            report["status"],
            "FORWARD_EVIDENCE_ACCUMULATION",
        )
        self.assertFalse(report["formal_research_sample_ready"])
        self.assertFalse(report["automatic_factor_promotion"])
        self.assertEqual(
            report["predictive_authority"],
            "NOT_AUTHORIZED",
        )
        self.assertIn(
            "No causal/predictive effect claim",
            report["research_note"],
        )


if __name__ == "__main__":
    unittest.main()
