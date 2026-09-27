import unittest

from scripts.point14_squad_hierarchy_rotation_v24 import (
    combine_hierarchy_and_transfer_prior,
    match_rotation_risk,
    squad_hierarchy,
    transfer_intent_decay,
    transfer_start_intent_prior,
)


class TestV24(unittest.TestCase):
    def test_transfer_prior_decays_with_rounds(self):
        self.assertEqual(transfer_intent_decay(0), 1.0)
        self.assertEqual(transfer_intent_decay(4), 0.6)
        self.assertEqual(transfer_intent_decay(8), 0.25)
        self.assertEqual(transfer_intent_decay(12), 0.05)

    def test_official_role_signal_dominates_transfer_prior(self):
        r = transfer_start_intent_prior(
            fee_club_percentile=None,
            fee_cohort_percentile=None,
            seasonal_spend_share=None,
            contract_years=None,
            positional_need=None,
            official_role_signal="starter",
        )
        self.assertEqual(r["level"], "HIGH")
        self.assertEqual(r["reason"], "OFFICIAL_ROLE_SIGNAL")

    def test_hierarchy_early_sample_is_unknown(self):
        r = squad_hierarchy(starts=2, team_matches=2, minutes=180)
        self.assertEqual(r["tier"], "UNKNOWN")
        self.assertEqual(r["status"], "HIERARCHY_EARLY_SAMPLE")

    def test_hierarchy_core_from_real_matches(self):
        r = squad_hierarchy(starts=7, team_matches=9, minutes=650)
        self.assertEqual(r["tier"], "CORE")

    def test_rotation_does_not_mutate_hierarchy(self):
        r = match_rotation_risk(
            rest_days=3,
            minutes_last_7d=180,
            matches_last_10d=3,
            matches_next_7d=2,
            historical_rotation_rate=0.4,
            next_match_importance_higher=True,
        )
        self.assertEqual(r["level"], "HIGH")
        self.assertTrue(r["does_not_mutate_squad_hierarchy"])

    def test_real_hierarchy_primary_over_transfer_prior(self):
        r = combine_hierarchy_and_transfer_prior(
            rounds_observed=8,
            hierarchy_tier="ROTATION",
            transfer_prior_level="HIGH",
        )
        self.assertEqual(r["authority"], "REAL_MATCH_HIERARCHY_PRIMARY")
        self.assertEqual(r["transfer_prior_decay_weight"], 0.25)


if __name__ == "__main__":
    unittest.main()
