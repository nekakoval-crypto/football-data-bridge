import unittest

from scripts.point14_in_tenure_lineup_audit_v19 import (
    audit_team,
    build_audit,
    conservative_in_tenure,
)


def tenure(team_id="33", start="2026-01-13", precision="DATE"):
    return {
        "team_id": team_id,
        "team_name": "Team",
        "coach_name": "Coach",
        "valid_from_utc": start,
        "valid_to_utc": "",
        "effective_precision": precision,
        "temporal_authority": "HISTORICAL_VERIFIED",
    }


def lineup(team_id="33", fixture="1", kickoff="2026-01-14T20:00:00+00:00", formation="4-2-3-1", count="11"):
    return {
        "team_id": team_id,
        "fixture_id": fixture,
        "kickoff_utc": kickoff,
        "formation": formation,
        "starting_xi_count": count,
        "home_team": "Team",
        "away_team": "Opponent",
        "coach_name": "Wrong Retrospective Coach",
        "temporal_authority": "RETROSPECTIVE_ONLY",
    }


class TestPoint14InTenureLineupAuditV19(unittest.TestCase):
    def test_date_boundary_day_is_excluded(self):
        row = tenure(start="2026-01-13", precision="DATE")
        self.assertFalse(
            conservative_in_tenure("2026-01-13T20:00:00+00:00", row)
        )
        self.assertTrue(
            conservative_in_tenure("2026-01-14T00:01:00+00:00", row)
        )

    def test_old_lineup_is_excluded(self):
        result = audit_team(
            tenure(),
            [lineup(kickoff="2026-01-12T20:00:00+00:00")],
        )
        self.assertEqual(
            result["status"],
            "CURRENT_REGIME_FORMATION_EVIDENCE_MISSING",
        )
        self.assertEqual(result["distinct_complete_fixtures"], 0)

    def test_two_fixtures_are_insufficient(self):
        rows = [
            lineup(fixture="1", kickoff="2026-01-14T20:00:00+00:00"),
            lineup(fixture="2", kickoff="2026-01-20T20:00:00+00:00"),
        ]
        result = audit_team(tenure(), rows)
        self.assertEqual(
            result["status"],
            "CURRENT_REGIME_FORMATION_EVIDENCE_INSUFFICIENT",
        )

    def test_three_complete_fixtures_are_available(self):
        rows = [
            lineup(fixture="1", kickoff="2026-01-14T20:00:00+00:00", formation="4-2-3-1"),
            lineup(fixture="2", kickoff="2026-01-20T20:00:00+00:00", formation="4-2-3-1"),
            lineup(fixture="3", kickoff="2026-01-27T20:00:00+00:00", formation="4-3-3"),
        ]
        result = audit_team(tenure(), rows)
        self.assertEqual(
            result["status"],
            "CURRENT_REGIME_FORMATION_EVIDENCE_AVAILABLE",
        )
        self.assertEqual(result["distinct_complete_fixtures"], 3)
        self.assertEqual(
            result["formation_distribution"][0],
            {"formation": "4-2-3-1", "matches": 2},
        )
        self.assertFalse(result["coach_metadata_used_as_tenure_truth"])

    def test_incomplete_xi_does_not_count_as_complete_evidence(self):
        rows = [
            lineup(fixture="1", count="10"),
            lineup(fixture="2", kickoff="2026-01-20T20:00:00+00:00", count="11"),
        ]
        result = audit_team(tenure(), rows)
        self.assertEqual(result["distinct_complete_fixtures"], 1)
        self.assertEqual(
            result["status"],
            "CURRENT_REGIME_FORMATION_EVIDENCE_INSUFFICIENT",
        )

    def test_only_verified_tenures_are_audited(self):
        verified = tenure()
        candidate = dict(tenure(team_id="47"))
        candidate["temporal_authority"] = "PROVIDER_CAREER_CANDIDATE"

        result = build_audit(
            [verified, candidate],
            [lineup(team_id="33")],
        )
        self.assertEqual(result["verified_tenure_count"], 1)
        self.assertEqual(len(result["teams"]), 1)


if __name__ == "__main__":
    unittest.main()
