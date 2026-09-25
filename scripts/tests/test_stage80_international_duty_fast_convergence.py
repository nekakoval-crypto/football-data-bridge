from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "stage80-international-duty-fast-convergence.yml"


class Stage80InternationalDutyFastConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_fast_rail_is_provider_free_after_existing_evidence(self):
        self.assertIn("needs: validate", self.text)
        self.assertIn("PROVIDER_FREE_EXISTING_EVIDENCE", self.text)
        self.assertIn("'historical_backfill_decoupled':True", self.text)
        self.assertIn("'provider_calls':0", self.text)
        self.assertNotIn("API_FOOTBALL_KEY:", self.text)

    def test_fast_rail_rebuilds_all_downstream_layers(self):
        required = [
            "stage80_international_duty_player_identity_join.py",
            "stage80_international_duty_player_temporal_club.py",
            "stage80_international_duty_pbk16_club_identity.py",
            "stage80_international_duty_return_load.py",
        ]
        for item in required:
            self.assertIn(item, self.text)

    def test_fast_rail_keeps_fail_closed_governance(self):
        self.assertIn("'workflow_run_depth_dependency':False", self.text)
        self.assertIn("'operational_betting_authority':False", self.text)
        self.assertIn("'probability_mutation':False", self.text)
        self.assertIn("'eligibility_mutation':False", self.text)
        self.assertIn("'stake_changes':False", self.text)


if __name__ == "__main__":
    unittest.main()
