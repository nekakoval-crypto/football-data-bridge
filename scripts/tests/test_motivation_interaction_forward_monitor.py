import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import motivation_interaction_forward_monitor as m


class MotivationInteractionForwardMonitorTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ops = self.root / "ops"
        self.ops.mkdir()

        self.config = (
            self.root
            / "pbk_motivation_interaction_v1_forward.json"
        )

        self.write_json(
            self.config,
            self.contract(),
        )

        self.write_json(
            self.ops
            / "motivation_interaction_specialist_v1.json",
            self.spec(),
        )

    def tearDown(self):
        self.temp.cleanup()

    def contract(self):
        return {
            "research_id":
                "PBK_MOTIVATION_INTERACTION_V1_FORWARD",
            "model_version":
                "PBK_MOTIVATION_INTERACTION_SPECIALIST_V1",
            "status":
                "FORWARD_REVIEW_CONTRACT",
            "authority":
                "RESEARCH",
            "frozen_candidate_source":
                "ops/motivation_interaction_specialist_v1.json",
            "required_candidate_status":
                "FROZEN_FORWARD_INTERACTION_CANDIDATE_READY",
            "frozen_model": {
                "formula":
                    "softmax(log(p_market_H)+z, log(p_market_D), log(p_market_A)-z)",
                "interactions":
                    list(m.SELECTED),
                "beta":
                    dict(m.EXPECTED_BETA),
                "refit_allowed":
                    False,
                "parameter_change_after_freeze":
                    False,
            },
            "prospective_inputs": {
                "market_prematch_journal":
                    "ops/generic_1x2_v1_forward_prematch.jsonl",
                "motivation_prematch_journal":
                    "ops/motivation_forward_prematch.jsonl",
                "motivation_postmatch_labels":
                    "ops/motivation_forward_labels.jsonl",
                "join_key":
                    "fixture_id",
                "historical_backfill":
                    False,
                "first_frozen_observation_only":
                    True,
                "observation_must_precede_kickoff":
                    True,
            },
            "forward_scope": {
                "review_unit":
                    "ACTIVE_INTERACTION_OBSERVATION",
            },
            "forward_review": {
                "diagnostic_checkpoints_active_rows":
                    [1, 2],
                "minimum_active_settled_rows_for_formal_review":
                    3,
                "minimum_outcomes_per_class":
                    1,
                "brier_strict_improvement_required":
                    True,
                "logloss_strict_improvement_required":
                    True,
                "maximum_absolute_class_calibration_error":
                    1.0,
                "interaction_direction_stability_required":
                    True,
                "manual_governance_review_required":
                    True,
                "automatic_canonical_promotion":
                    False,
            },
            "guards": {
                "unknown_not_zero":
                    True,
                "no_lookahead":
                    True,
                "prematch_frozen_required":
                    True,
                "postmatch_labels_separate":
                    True,
                "market_probability_is_baseline_not_pbk_opinion":
                    True,
                "standalone_motivation_v1_rejected":
                    True,
                "standalone_motivation_v2_rejected":
                    True,
                "creates_signal":
                    False,
                "predictive_authority":
                    "NOT_AUTHORIZED",
                "operational_betting_authority":
                    False,
                "probability_mutation_authorized":
                    False,
                "eligibility_mutation_authorized":
                    False,
                "value_or_ev_authorized":
                    False,
                "stake_changes_authorized":
                    False,
                "r1_r2_r3_changes_authorized":
                    False,
                "production_integration_authorized":
                    False,
                "ui_integration_authorized":
                    False,
            },
            "outputs": {
                "prematch_journal":
                    "contract_prematch.jsonl",
                "settlement_journal":
                    "contract_settlements.jsonl",
                "performance_report":
                    "contract_performance.json",
            },
        }

    def spec(self):
        return {
            "status":
                "FROZEN_FORWARD_INTERACTION_CANDIDATE_READY",
            "selected_interactions":
                list(m.SELECTED),
            "frozen_candidate": {
                "interactions":
                    list(m.SELECTED),
                "beta":
                    dict(m.EXPECTED_BETA),
                "parameters_may_change_after_freeze":
                    False,
            },
            "authorization": {
                "forward_review_allowed":
                    True,
                "predictive_authority":
                    "NOT_AUTHORIZED",
            },
        }

    def write_json(self, path, payload):
        Path(path).write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def write_jsonl(self, name, rows):
        (
            self.ops / name
        ).write_text(
            "".join(
                json.dumps(row) + "\n"
                for row in rows
            ),
            encoding="utf-8",
        )

    def sources(
        self,
        fixture_id="999",
        pressure_home="HIGH",
        pressure_away="LOW",
        home_rank=10,
        away_rank=1,
        home_form="WWWWW",
        away_form="LLLLL",
    ):
        motivation = {
            "event_id":
                f"mot-{fixture_id}",
            "event_type":
                "MOTIVATION_PREMATCH_FROZEN",
            "fixture_id":
                fixture_id,
            "frozen_at_utc":
                "2026-09-24T17:20:00Z",
            "payload": {
                "fixture_id":
                    fixture_id,
                "kickoff_utc":
                    "2026-09-24T18:00:00Z",
                "home_team":
                    "Alpha",
                "away_team":
                    "Beta",
                "comparison": {
                    "home_pressure":
                        pressure_home,
                    "away_pressure":
                        pressure_away,
                },
                "home": {
                    "standings": {
                        "rank":
                            home_rank,
                        "form":
                            home_form,
                    }
                },
                "away": {
                    "standings": {
                        "rank":
                            away_rank,
                        "form":
                            away_form,
                    }
                },
            },
        }

        market = {
            "event_id":
                f"market-{fixture_id}",
            "event_type":
                "GENERIC_1X2_V1_PREMATCH_FROZEN",
            "fixture_id":
                fixture_id,
            "frozen_at_utc":
                "2026-09-24T16:00:00Z",
            "payload": {
                "fixture_id":
                    fixture_id,
                "kickoff_utc":
                    "2026-09-24T18:00:00Z",
                "observed_at_utc":
                    "2026-09-24T15:55:00Z",
                "p_market": {
                    "H": 0.50,
                    "D": 0.30,
                    "A": 0.20,
                },
            },
        }

        self.write_jsonl(
            "motivation_forward_prematch.jsonl",
            [motivation],
        )

        self.write_jsonl(
            "generic_1x2_v1_forward_prematch.jsonl",
            [market],
        )

    def before(self):
        return datetime(
            2026, 9, 24, 17, 30,
            tzinfo=timezone.utc,
        )

    def after(self):
        return datetime(
            2026, 9, 24, 20, 0,
            tzinfo=timezone.utc,
        )

    def test_frozen_config_controls_output_names(self):
        self.sources()

        result = m.run(
            observed_at=self.before(),
            ops=self.ops,
            config_path=self.config,
        )

        self.assertEqual(
            result["prematch_events_created"],
            1,
        )

        self.assertTrue(
            (
                self.ops
                / "contract_prematch.jsonl"
            ).exists()
        )

        self.assertTrue(
            (
                self.ops
                / "contract_performance.json"
            ).exists()
        )

        self.assertFalse(
            (
                self.ops
                / "motivation_interaction_v1_forward_last_run.json"
            ).exists()
        )

    def test_exact_candidate_and_beta_are_frozen(self):
        self.sources()

        m.run(
            observed_at=self.before(),
            ops=self.ops,
            config_path=self.config,
        )

        _, rows = m.read_jsonl(
            self.ops
            / "contract_prematch.jsonl"
        )

        payload = rows[0]["payload"]

        self.assertEqual(
            payload["interactions"],
            {
                "HIGH_PRESSURE_X_FORM_ALIGNMENT":
                    1.0,
                "HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE":
                    1.0,
            },
        )

        self.assertEqual(
            payload["beta"],
            m.EXPECTED_BETA,
        )

        self.assertTrue(
            payload[
                "active_interaction_observation"
            ]
        )

        self.assertFalse(
            payload["parameters_refit"]
        )

        self.assertEqual(
            payload["predictive_authority"],
            "NOT_AUTHORIZED",
        )

    def test_zero_interaction_does_not_expand_active_sample(self):
        self.sources(
            pressure_home="LOW",
            pressure_away="LOW",
            home_rank=1,
            away_rank=2,
            home_form="WWWWW",
            away_form="WWWWW",
        )

        result = m.run(
            observed_at=self.before(),
            ops=self.ops,
            config_path=self.config,
        )

        self.assertEqual(
            result["prematch_events_total"],
            1,
        )

        self.assertEqual(
            result["active_prematch_rows"],
            0,
        )

    def test_missed_match_cannot_be_backfilled(self):
        self.sources()

        result = m.run(
            observed_at=self.after(),
            ops=self.ops,
            config_path=self.config,
        )

        self.assertEqual(
            result["prematch_events_created"],
            0,
        )

        self.assertEqual(
            result[
                "skipped_after_kickoff_no_backfill"
            ],
            1,
        )

    def test_settlement_is_separate_and_prematch_immutable(self):
        self.sources()

        m.run(
            observed_at=self.before(),
            ops=self.ops,
            config_path=self.config,
        )

        prematch_path = (
            self.ops
            / "contract_prematch.jsonl"
        )

        frozen = prematch_path.read_bytes()

        self.write_jsonl(
            "motivation_forward_labels.jsonl",
            [{
                "event_id":
                    "label-999",
                "event_type":
                    "MOTIVATION_POSTMATCH_LABEL",
                "fixture_id":
                    "999",
                "payload": {
                    "fixture_id":
                        "999",
                    "match_result":
                        "HOME_WIN",
                    "prematch_evidence_mutated":
                        False,
                },
            }],
        )

        result = m.run(
            observed_at=self.after(),
            ops=self.ops,
            config_path=self.config,
        )

        self.assertEqual(
            result["settlements_created"],
            1,
        )

        self.assertEqual(
            prematch_path.read_bytes(),
            frozen,
        )

        self.assertTrue(
            (
                self.ops
                / "contract_settlements.jsonl"
            ).exists()
        )

        self.assertEqual(
            result["predictive_authority"],
            "NOT_AUTHORIZED",
        )

    def test_insufficient_sample_fails_closed(self):
        self.sources()

        self.write_jsonl(
            "motivation_forward_labels.jsonl",
            [],
        )

        result = m.run(
            observed_at=self.before(),
            ops=self.ops,
            config_path=self.config,
        )

        self.assertEqual(
            result["status"],
            "INSUFFICIENT_FORWARD_SAMPLE",
        )

        self.assertFalse(
            result["automatic_canonical_promotion"]
        )

        self.assertEqual(
            result["predictive_authority"],
            "NOT_AUTHORIZED",
        )

    def test_contract_authority_drift_fails_closed(self):
        broken = self.contract()

        broken["guards"][
            "value_or_ev_authorized"
        ] = True

        with self.assertRaises(ValueError):
            m.validate_contract(broken)

    def test_spec_beta_drift_fails_closed(self):
        contract = m.validate_contract(
            self.contract()
        )

        broken = self.spec()

        broken["frozen_candidate"]["beta"][
            m.SELECTED[0]
        ] = 0.25

        with self.assertRaises(ValueError):
            m.validate_spec(
                broken,
                contract,
            )


if __name__ == "__main__":
    unittest.main()
