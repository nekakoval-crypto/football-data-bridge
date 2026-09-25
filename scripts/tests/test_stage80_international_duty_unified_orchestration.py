from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "stage80-international-duty-unified-orchestration.yml"


class Stage80InternationalDutyUnifiedOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_jobs_follow_single_needs_chain(self):
        expected = [
            ("provider_catalog", "validate"),
            ("source_allowlist", "provider_catalog"),
            ("fixture_backfill", "source_allowlist"),
            ("evidence_backlog", "fixture_backfill"),
            ("evidence_capture", "evidence_backlog"),
            ("identity_join", "evidence_capture"),
            ("temporal_club", "identity_join"),
            ("pbk16_club_identity", "temporal_club"),
            ("return_load", "pbk16_club_identity"),
            ("convergence", "return_load"),
        ]
        for job, dependency in expected:
            pattern = rf"(?ms)^  {re.escape(job)}:\n.*?^    needs: {re.escape(dependency)}$"
            self.assertRegex(self.text, pattern)

    def test_unified_workflow_does_not_use_workflow_run(self):
        on_block = self.text.split("permissions:", 1)[0]
        self.assertNotIn("workflow_run:", on_block)
        self.assertIn("workflow_dispatch:", on_block)
        self.assertIn("schedule:", on_block)

    def test_provider_calls_are_bounded_and_shared_budget_is_preserved(self):
        self.assertIn("API_FOOTBALL_MAX_REAL_CALLS: '1'", self.text)
        self.assertIn("STAGE80_INTL_DUTY_FIXTURE_MAX_API_CALLS: '20'", self.text)
        self.assertIn("STAGE80_INTL_DUTY_PLAYER_EVIDENCE_MAX_API_CALLS: '750'", self.text)
        self.assertIn("STAGE71_MAX_DAILY_API_CALLS: '7000'", self.text)
        self.assertIn("STAGE80_INTL_DUTY_FIXTURE_PROTECTED_CALLS: '512'", self.text)
        self.assertIn("STAGE80_INTL_DUTY_PLAYER_EVIDENCE_PROTECTED_CALLS: '512'", self.text)

    def test_convergence_proof_is_fail_closed_and_non_operational(self):
        self.assertIn("'orchestration':'SINGLE_WORKFLOW_JOBS_NEEDS'", self.text)
        self.assertIn("'workflow_run_depth_dependency':False", self.text)
        self.assertIn("'operational_betting_authority':False", self.text)
        self.assertIn("'probability_mutation':False", self.text)
        self.assertIn("'eligibility_mutation':False", self.text)
        self.assertIn("'stake_changes':False", self.text)


if __name__ == "__main__":
    unittest.main()
