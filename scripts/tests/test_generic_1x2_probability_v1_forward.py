import json
import tempfile
import unittest
from pathlib import Path

from scripts import generic_1x2_probability_v1_forward as fwd


VALIDATED = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
SHADOW = [
    "Austrian Bundesliga", "Belgian Pro League", "Danish Superliga", "A Lyga",
    "Virsliga", "Eredivisie", "Eliteserien", "Ekstraklasa", "Primeira Liga",
    "Super Lig", "Scottish Premiership",
]


class Generic1X2ForwardTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "research_id": "PBK_GENERIC_1X2_PROBABILITY_V1_FORWARD",
            "model_version": "PBK_GENERIC_1X2_PROBABILITY_V1",
            "scope": {
                "locked_total_leagues": 16,
                "tracked_leagues": VALIDATED + SHADOW,
                "validated_domain_leagues": VALIDATED,
                "extended_shadow_leagues": SHADOW,
            },
            "frozen_model": {"alpha_h": -0.018, "alpha_d": 0.0, "alpha_a": -0.004},
            "capture_policy": {"snapshot": "FIRST_COMPLETE_VALID_BET365_PREMATCH_OBSERVATION"},
            "forward_review": {
                "formal_review_domain": "VALIDATED_DOMAIN",
                "shadow_domain": "EXTENDED_SHADOW_RESEARCH",
                "shadow_excluded_from_official_gate": True,
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

    def settled(self, event, outcome="H"):
        return fwd.settlement_to_event(
            {"fixture_id": event["fixture_id"], "result": outcome,
             "settled_at_utc": "2026-09-20T17:00:00Z"},
            {event["fixture_id"]: event},
        )

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

    def test_all_16_locked_leagues_are_tracked(self):
        self.assertEqual(len(self.cfg["scope"]["tracked_leagues"]), 16)
        self.assertEqual(
            set(self.cfg["scope"]["tracked_leagues"]),
            set(self.cfg["scope"]["validated_domain_leagues"]) | set(self.cfg["scope"]["extended_shadow_leagues"]),
        )

    def test_extended_league_is_accepted_as_shadow_not_official(self):
        row = dict(self.row)
        row["league"] = "Eredivisie"
        event = self.event(row)
        self.assertEqual(event["payload"]["monitoring_domain"], "EXTENDED_SHADOW_RESEARCH")
        self.assertFalse(event["payload"]["formal_review_eligible"])

    def test_big5_is_validated_domain(self):
        event = self.event()
        self.assertEqual(event["payload"]["monitoring_domain"], "VALIDATED_DOMAIN")
        self.assertTrue(event["payload"]["formal_review_eligible"])

    def test_outside_locked_16_scope_rejected(self):
        row = dict(self.row)
        row["league"] = "Ukrainian Premier League"
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

    def test_settlement_carries_domain_and_scores(self):
        prematch = self.event()
        settled = self.settled(prematch, "H")
        self.assertEqual(settled["payload"]["monitoring_domain"], "VALIDATED_DOMAIN")
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
        settlement = self.settled(prematch, "H")
        report = fwd.performance_report(self.cfg, [prematch], [settlement])
        self.assertEqual(report["status"], "COLLECTING")
        self.assertFalse(report["official_forward_review"]["formal_review_sample_ready"])
        self.assertFalse(report["policy"]["automatic_canonical_promotion"])
        self.assertFalse(report["policy"]["profitability_or_roi_conclusion"])

    def test_shadow_rows_never_contaminate_official_gate(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["forward_review"]["minimum_settled_rows"] = 3
        cfg["forward_review"]["minimum_settled_outcomes_per_class"] = 1
        prematch, settlements = [], []
        for index, outcome in enumerate(("H", "D", "A"), start=1):
            row = dict(self.row)
            row["fixture_id"] = str(2000 + index)
            event = fwd.observation_to_event(row, cfg, process_time=self.process_time)
            prematch.append(event)
            settlements.append(self.settled(event, outcome))

        official_only = fwd.performance_report(cfg, prematch, settlements)

        shadow_row = dict(self.row)
        shadow_row["fixture_id"] = "3001"
        shadow_row["league"] = "Eredivisie"
        shadow_event = fwd.observation_to_event(shadow_row, cfg, process_time=self.process_time)
        shadow_settlement = self.settled(shadow_event, "A")
        mixed = fwd.performance_report(
            cfg, prematch + [shadow_event], settlements + [shadow_settlement])

        self.assertEqual(mixed["official_forward_review"]["settled_rows"], 3)
        self.assertEqual(mixed["extended_shadow_research"]["settled_rows"], 1)
        self.assertEqual(mixed["all_domains"]["settled_rows"], 4)
        self.assertEqual(
            mixed["official_forward_review"]["scores"],
            official_only["official_forward_review"]["scores"],
        )
        self.assertTrue(mixed["policy"]["shadow_excluded_from_official_gate"])

    def test_review_ready_never_auto_promotes_canonical(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["forward_review"]["minimum_settled_rows"] = 3
        cfg["forward_review"]["minimum_settled_outcomes_per_class"] = 1
        events, settlements = [], []
        for index, outcome in enumerate(("H", "D", "A"), start=1):
            row = dict(self.row)
            row["fixture_id"] = str(4000 + index)
            event = fwd.observation_to_event(row, cfg, process_time=self.process_time)
            events.append(event)
            settlements.append(self.settled(event, outcome))
        report = fwd.performance_report(cfg, events, settlements)
        self.assertIn(report["status"], {"FORWARD_REVIEW_READY_PASS", "FORWARD_REVIEW_READY_FAIL"})
        self.assertFalse(report["policy"]["automatic_canonical_promotion"])
        self.assertTrue(report["policy"]["manual_governance_review_required"])

    def test_scope_guard_fails_if_shadow_and_validated_overlap(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["scope"]["extended_shadow_leagues"].append("Premier League")
        with self.assertRaisesRegex(ValueError, "disjoint"):
            fwd.monitoring_domain(cfg, "Premier League")

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
            cfg = json.loads(json.dumps(self.cfg))
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
