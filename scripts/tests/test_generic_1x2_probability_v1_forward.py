import json
import tempfile
import unittest
from pathlib import Path

from scripts import generic_1x2_probability_v1_forward as fwd


class Generic1X2ForwardTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "research_id": "PBK_GENERIC_1X2_PROBABILITY_V1_FORWARD",
            "model_version": "PBK_GENERIC_1X2_PROBABILITY_V1",
            "scope": {"leagues": ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]},
            "frozen_model": {"alpha_h": -0.018, "alpha_d": 0.0, "alpha_a": -0.004},
            "capture_policy": {"snapshot": "FIRST_COMPLETE_VALID_BET365_PREMATCH_OBSERVATION"},
            "forward_review": {
                "diagnostic_checkpoints": [250, 500],
                "minimum_settled_rows": 1000,
                "minimum_settled_outcomes_per_class": 150,
                "maximum_absolute_class_calibration_error": 0.03,
            },
            "guards": {"probability_sum_tolerance": 1e-9},
        }
        self.row = {
            "fixture_id": "1001",
            "league": "Premier League",
            "home_team": "Home",
            "away_team": "Away",
            "kickoff_utc": "2026-09-20T15:00:00Z",
            "observed_at_utc": "2026-09-20T12:00:00Z",
            "b365_home": "2.10",
            "b365_draw": "3.40",
            "b365_away": "3.60",
        }
        self.process_time = "2026-09-20T12:01:00Z"

    def event(self, row=None):
        return fwd.observation_to_event(row or self.row, self.cfg, process_time=self.process_time)

    def test_probability_vectors_sum_to_one(self):
        event = self.event()
        self.assertAlmostEqual(sum(event["payload"]["p_market"].values()), 1.0, places=14)
        self.assertAlmostEqual(sum(event["payload"]["p_m1"].values()), 1.0, places=14)

    def test_complete_bet365_required(self):
        row = dict(self.row)
        row["b365_draw"] = ""
        with self.assertRaisesRegex(ValueError, "complete valid Bet365"):
            self.event(row)

    def test_prematch_event_has_no_outcome_value_or_signal_authority(self):
        payload = self.event()["payload"]
        self.assertNotIn("result", payload)
        self.assertNotIn("ev", payload)
        self.assertFalse(payload["creates_signal"])
        self.assertFalse(payload["value_authorized"])
        self.assertFalse(payload["stake_changes_authorized"])
        self.assertFalse(payload["canonical_promotion_authorized"])

    def test_postkickoff_and_historical_backfill_rejected(self):
        post = dict(self.row)
        post["observed_at_utc"] = "2026-09-20T15:01:00Z"
        with self.assertRaisesRegex(ValueError, "post-kickoff"):
            self.event(post)
        with self.assertRaisesRegex(ValueError, "historical_backfill_forbidden"):
            fwd.observation_to_event(self.row, self.cfg, process_time="2026-09-20T15:01:00Z")

    def test_outside_scope_rejected(self):
        row = dict(self.row)
        row["league"] = "Eredivisie"
        with self.assertRaisesRegex(ValueError, "outside_scope"):
            self.event(row)

    def test_first_valid_observation_is_immutable(self):
        first = self.event()
        later = dict(self.row)
        later["b365_home"] = "1.90"
        later["observed_at_utc"] = "2026-09-20T13:00:00Z"
        added, rejected = fwd.freeze_observations(
            [self.row, later], self.cfg, [], process_time="2026-09-20T13:01:00Z")
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["payload"]["b365_home"], first["payload"]["b365_home"])
        self.assertEqual(rejected[0]["reason"], "already_frozen")

    def test_existing_frozen_fixture_not_rewritten(self):
        existing = [self.event()]
        changed = dict(self.row)
        changed["b365_home"] = "1.70"
        added, rejected = fwd.freeze_observations(
            [changed], self.cfg, existing, process_time="2026-09-20T13:00:00Z")
        self.assertEqual(added, [])
        self.assertEqual(rejected[0]["reason"], "already_frozen")

    def test_settlement_uses_frozen_vectors_and_scores(self):
        prematch = self.event()
        settled = fwd.settlement_to_event(
            {"fixture_id": "1001", "result": "H", "settled_at_utc": "2026-09-20T17:00:00Z"},
            {"1001": prematch})
        self.assertEqual(settled["payload"]["result"], "H")
        self.assertGreaterEqual(settled["payload"]["brier_m1"], 0.0)
        self.assertGreaterEqual(settled["payload"]["logloss_m1"], 0.0)
        self.assertFalse(settled["payload"]["profitability_tested"])
        self.assertFalse(settled["payload"]["value_authorized"])

    def test_settlement_before_or_at_kickoff_rejected(self):
        with self.assertRaisesRegex(ValueError, "after kickoff"):
            fwd.settlement_to_event(
                {"fixture_id": "1001", "result": "H", "settled_at_utc": "2026-09-20T15:00:00Z"},
                {"1001": self.event()})

    def test_report_collecting_before_locked_sample(self):
        prematch = self.event()
        settlement = fwd.settlement_to_event(
            {"fixture_id": "1001", "result": "H", "settled_at_utc": "2026-09-20T17:00:00Z"},
            {"1001": prematch})
        report = fwd.performance_report(self.cfg, [prematch], [settlement])
        self.assertEqual(report["status"], "COLLECTING")
        self.assertFalse(report["formal_review_sample_ready"])
        self.assertFalse(report["policy"]["automatic_canonical_promotion"])
        self.assertFalse(report["policy"]["profitability_or_roi_conclusion"])

    def test_review_ready_never_auto_promotes_canonical(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["forward_review"]["minimum_settled_rows"] = 3
        cfg["forward_review"]["minimum_settled_outcomes_per_class"] = 1
        events, settlements = [], []
        for index, outcome in enumerate(("H", "D", "A"), start=1):
            row = dict(self.row)
            row["fixture_id"] = str(2000 + index)
            event = fwd.observation_to_event(row, cfg, process_time=self.process_time)
            settlement = fwd.settlement_to_event(
                {"fixture_id": row["fixture_id"], "result": outcome,
                 "settled_at_utc": "2026-09-20T17:00:00Z"},
                {row["fixture_id"]: event})
            events.append(event)
            settlements.append(settlement)
        report = fwd.performance_report(cfg, events, settlements)
        self.assertIn(report["status"], {"FORWARD_REVIEW_READY_PASS", "FORWARD_REVIEW_READY_FAIL"})
        self.assertFalse(report["policy"]["automatic_canonical_promotion"])
        self.assertTrue(report["policy"]["manual_governance_review_required"])

    def test_load_contract_fails_closed_on_alpha_drift(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            historical = td / "result.json"
            historical.write_text(json.dumps({
                "final_verdict": "PASS_HISTORICAL_PROBABILITY_GATE",
                "execution": {"no_posthoc_tuning": True},
                "authorization": {"production_integration_authorized": False},
                "fit": {"alpha_h": -0.018, "alpha_d": 0.0, "alpha_a": -0.004}
            }), encoding="utf-8")
            cfg = dict(self.cfg)
            cfg.update({
                "historical_result_required_verdict": "PASS_HISTORICAL_PROBABILITY_GATE",
                "historical_result_path": str(historical),
                "frozen_model": {"alpha_h": -0.017, "alpha_d": 0.0, "alpha_a": -0.004},
            })
            config = td / "config.json"
            config.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen alpha_h differs"):
                fwd.load_contract(config)


if __name__ == "__main__":
    unittest.main()
