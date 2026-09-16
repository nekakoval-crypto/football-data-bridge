import json
import tempfile
import unittest
from pathlib import Path

from scripts import generic_1x2_probability_v1_forward as fwd


BIG5 = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
EXTENDED = [
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
                "tracked_leagues": BIG5 + EXTENDED,
                "historical_big5_pooled_leagues": BIG5,
                "historically_unvalidated_leagues": EXTENDED,
            },
            "frozen_model": {"alpha_h": -0.018, "alpha_d": 0.0, "alpha_a": -0.004},
            "capture_policy": {"snapshot": "FIRST_COMPLETE_VALID_BET365_PREMATCH_OBSERVATION"},
            "forward_review": {
                "review_unit": "LEAGUE",
                "pooled_big5_diagnostic_only": True,
                "combined_16_league_verdict": False,
                "diagnostic_checkpoints_per_league": [250, 500],
                "minimum_settled_rows_per_league": 1000,
                "minimum_settled_outcomes_per_class_per_league": 150,
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

    def event(self, row=None, cfg=None):
        return fwd.observation_to_event(
            row or self.row, cfg or self.cfg, process_time=self.process_time)

    def settled(self, event, outcome="H"):
        return fwd.settlement_to_event(
            {
                "fixture_id": event["fixture_id"],
                "result": outcome,
                "settled_at_utc": "2026-09-20T17:00:00Z",
            },
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

    def test_no_value_signal_or_canonical_authority(self):
        payload = self.event()["payload"]
        self.assertNotIn("result", payload)
        self.assertNotIn("ev", payload)
        self.assertFalse(payload["creates_signal"])
        self.assertFalse(payload["value_authorized"])
        self.assertFalse(payload["stake_changes_authorized"])
        self.assertFalse(payload["canonical_promotion_authorized"])

    def test_postkickoff_and_backfill_rejected(self):
        post = dict(self.row)
        post["observed_at_utc"] = "2026-09-20T15:01:00Z"
        with self.assertRaisesRegex(ValueError, "post-kickoff"):
            self.event(post)
        with self.assertRaisesRegex(ValueError, "historical_backfill_forbidden"):
            fwd.observation_to_event(
                self.row, self.cfg, process_time="2026-09-20T15:01:00Z")

    def test_all_16_leagues_are_tracked(self):
        _, _, tracked = fwd._scope_sets(self.cfg)
        self.assertEqual(len(tracked), 16)

    def test_big5_has_pooled_historical_evidence_but_not_individual_validation(self):
        event = self.event()
        self.assertEqual(
            event["payload"]["historical_evidence_status"],
            "HISTORICAL_BIG5_POOL_MEMBER",
        )
        self.assertTrue(event["payload"]["league_forward_review_eligible"])

    def test_extended_has_no_historical_validation_but_is_forward_eligible(self):
        row = dict(self.row)
        row["league"] = "Eredivisie"
        event = self.event(row)
        self.assertEqual(
            event["payload"]["historical_evidence_status"],
            "NO_HISTORICAL_LEAGUE_VALIDATION",
        )
        self.assertTrue(event["payload"]["league_forward_review_eligible"])

    def test_outside_locked_16_scope_rejected(self):
        row = dict(self.row)
        row["league"] = "Ukrainian Premier League"
        with self.assertRaisesRegex(ValueError, "outside_scope"):
            self.event(row)

    def test_first_valid_observation_is_immutable(self):
        later = dict(self.row)
        later["b365_home"] = "1.90"
        later["observed_at_utc"] = "2026-09-20T13:00:00Z"
        added, rejected = fwd.freeze_observations(
            [self.row, later], self.cfg, [], process_time="2026-09-20T13:01:00Z")
        self.assertEqual(len(added), 1)
        self.assertEqual(rejected[0]["reason"], "already_frozen")

    def test_settlement_keeps_league_identity_and_scores(self):
        event = self.event()
        settlement = self.settled(event, "H")
        self.assertEqual(settlement["payload"]["league"], "Premier League")
        self.assertGreaterEqual(settlement["payload"]["brier_m1"], 0.0)
        self.assertGreaterEqual(settlement["payload"]["logloss_m1"], 0.0)
        self.assertFalse(settlement["payload"]["profitability_tested"])

    def test_each_league_gets_own_review_record(self):
        report = fwd.performance_report(self.cfg, [], [])
        self.assertEqual(set(report["league_reviews"]), set(BIG5 + EXTENDED))
        self.assertEqual(len(report["league_reviews"]), 16)
        self.assertEqual(report["status"], "PER_LEAGUE_FORWARD_REVIEW")
        self.assertFalse(report["policy"]["pooled_big5_forward_verdict"])
        self.assertFalse(report["policy"]["combined_16_league_verdict"])

    def test_league_metrics_are_isolated(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["forward_review"]["minimum_settled_rows_per_league"] = 3
        cfg["forward_review"]["minimum_settled_outcomes_per_class_per_league"] = 1
        prematch, settlements = [], []
        for index, outcome in enumerate(("H", "D", "A"), start=1):
            row = dict(self.row)
            row["fixture_id"] = str(2000 + index)
            event = self.event(row, cfg)
            prematch.append(event)
            settlements.append(self.settled(event, outcome))

        base = fwd.performance_report(cfg, prematch, settlements)
        pl_before = base["league_reviews"]["Premier League"]

        erow = dict(self.row)
        erow["fixture_id"] = "3001"
        erow["league"] = "Eredivisie"
        eevent = self.event(erow, cfg)
        esettled = self.settled(eevent, "A")
        mixed = fwd.performance_report(
            cfg, prematch + [eevent], settlements + [esettled])

        pl_after = mixed["league_reviews"]["Premier League"]
        eredivisie = mixed["league_reviews"]["Eredivisie"]
        self.assertEqual(pl_before["scores"], pl_after["scores"])
        self.assertEqual(pl_after["settled_rows"], 3)
        self.assertEqual(eredivisie["settled_rows"], 1)
        self.assertFalse(eredivisie["formal_review_sample_ready"])

    def test_one_league_can_be_review_ready_while_another_collects(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["forward_review"]["minimum_settled_rows_per_league"] = 3
        cfg["forward_review"]["minimum_settled_outcomes_per_class_per_league"] = 1
        prematch, settlements = [], []
        for index, outcome in enumerate(("H", "D", "A"), start=1):
            row = dict(self.row)
            row["fixture_id"] = str(4000 + index)
            event = self.event(row, cfg)
            prematch.append(event)
            settlements.append(self.settled(event, outcome))

        erow = dict(self.row)
        erow["fixture_id"] = "5001"
        erow["league"] = "Eredivisie"
        eevent = self.event(erow, cfg)
        prematch.append(eevent)
        settlements.append(self.settled(eevent, "H"))

        report = fwd.performance_report(cfg, prematch, settlements)
        self.assertIn(
            report["league_reviews"]["Premier League"]["status"],
            {"FORWARD_REVIEW_READY_PASS", "FORWARD_REVIEW_READY_FAIL"},
        )
        self.assertEqual(
            report["league_reviews"]["Eredivisie"]["status"],
            "COLLECTING",
        )

    def test_pooled_big5_is_diagnostic_only(self):
        event = self.event()
        settlement = self.settled(event, "H")
        report = fwd.performance_report(self.cfg, [event], [settlement])
        self.assertEqual(report["pooled_big5_diagnostic"]["status"], "DIAGNOSTIC_ONLY")
        self.assertEqual(
            report["pooled_big5_diagnostic"]["purpose"],
            "POOLED_DIAGNOSTIC_ONLY_NOT_AN_OFFICIAL_FORWARD_VERDICT",
        )

    def test_scope_guard_fails_on_overlap(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["scope"]["historically_unvalidated_leagues"].append("Premier League")
        with self.assertRaisesRegex(ValueError, "disjoint"):
            fwd._scope_sets(cfg)

    def test_load_contract_fails_closed_on_non_league_review_unit(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            historical = td / "result.json"
            historical.write_text(json.dumps({
                "final_verdict": "PASS_HISTORICAL_PROBABILITY_GATE",
                "execution": {"no_posthoc_tuning": True},
                "authorization": {"production_integration_authorized": False},
                "fit": {"alpha_h": -0.018, "alpha_d": 0.0, "alpha_a": -0.004},
            }), encoding="utf-8")
            cfg = json.loads(json.dumps(self.cfg))
            cfg.update({
                "historical_result_required_verdict": "PASS_HISTORICAL_PROBABILITY_GATE",
                "historical_result_path": str(historical),
            })
            cfg["forward_review"]["review_unit"] = "POOL"
            config = td / "config.json"
            config.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "review unit must remain LEAGUE"):
                fwd.load_contract(config)

    def test_load_contract_fails_closed_on_alpha_drift(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            historical = td / "result.json"
            historical.write_text(json.dumps({
                "final_verdict": "PASS_HISTORICAL_PROBABILITY_GATE",
                "execution": {"no_posthoc_tuning": True},
                "authorization": {"production_integration_authorized": False},
                "fit": {"alpha_h": -0.018, "alpha_d": 0.0, "alpha_a": -0.004},
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
