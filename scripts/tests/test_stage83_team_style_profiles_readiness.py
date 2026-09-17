from __future__ import annotations

import unittest

from scripts.stage83_team_style_profiles_readiness import build_readiness


class Stage83ReadinessTests(unittest.TestCase):
    def test_waiting_without_stage82_evidence(self):
        result = build_readiness(
            source_evidence_rows=0,
            profiles_payload=None,
        )

        self.assertEqual(result["status"], "WAITING_FOR_STAGE82_EVIDENCE")
        self.assertEqual(result["team_profile_coverage_pct"], 0.0)
        self.assertEqual(result["provider_calls_added"], 0)

    def test_partial_when_evidence_exists_but_profiles_missing(self):
        result = build_readiness(
            source_evidence_rows=10,
            profiles_payload=None,
        )

        self.assertEqual(result["status"], "PARTIAL")
        self.assertFalse(result["profiles_present"])

    def test_attention_when_profiles_have_no_eligible_teams(self):
        result = build_readiness(
            source_evidence_rows=10,
            profiles_payload={
                "version": "PBK_STAGE83_TEAM_STYLE_OPERATIONAL_PROFILES_V1",
                "before_utc": "2026-09-17T12:00:00+00:00",
                "teams_seen": 3,
                "teams_with_eligible_evidence": 0,
                "total_eligible_team_matches": 0,
            },
        )

        self.assertEqual(result["status"], "ATTENTION")
        self.assertEqual(result["teams_seen"], 3)
        self.assertEqual(result["team_profile_coverage_pct"], 0.0)

    def test_partial_when_only_some_teams_are_eligible(self):
        result = build_readiness(
            source_evidence_rows=20,
            profiles_payload={
                "version": "PBK_STAGE83_TEAM_STYLE_OPERATIONAL_PROFILES_V1",
                "before_utc": "2026-09-17T12:00:00+00:00",
                "teams_seen": 4,
                "teams_with_eligible_evidence": 3,
                "total_eligible_team_matches": 25,
            },
        )

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["team_profile_coverage_pct"], 75.0)

    def test_ready_when_all_seen_teams_have_eligible_profiles(self):
        result = build_readiness(
            source_evidence_rows=40,
            profiles_payload={
                "version": "PBK_STAGE83_TEAM_STYLE_OPERATIONAL_PROFILES_V1",
                "before_utc": "2026-09-17T12:00:00+00:00",
                "teams_seen": 4,
                "teams_with_eligible_evidence": 4,
                "total_eligible_team_matches": 40,
            },
        )

        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["team_profile_coverage_pct"], 100.0)
        self.assertEqual(result["style_scale_calibrated"], False)
        self.assertEqual(result["creates_signal"], False)


if __name__ == "__main__":
    unittest.main()
