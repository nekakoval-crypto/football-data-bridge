import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import stage80_player_layer_completion as p


class PlayerLayerCompletionTests(unittest.TestCase):

    def xi(self, start=1):
        return json.dumps([
            {"player": {"id": i, "name": f"P{i}"}}
            for i in range(start, start + 11)
        ])

    def test_parse_xi_requires_exact_unique_eleven(self):
        self.assertEqual(len(p.parse_xi(self.xi(1))), 11)
        self.assertEqual(p.parse_xi("[]"), [])
        duplicate = [{"player": {"id": 1}} for _ in range(11)]
        self.assertEqual(p.parse_xi(json.dumps(duplicate)), [])

    def test_availability_is_retrospective_only(self):
        rows = p.build_availability_rows([{
            "fixture_id": "10",
            "kickoff_utc": "2025-01-01T12:00:00Z",
            "team_id": "20",
            "team_name": "T",
            "player_id": "30",
            "player_name": "P",
            "type": "Missing Fixture",
            "reason": "Hamstring",
            "retrieved_at_utc": "2026-09-20T00:00:00Z",
        }])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["temporal_authority"], "RETROSPECTIVE_ONLY")
        self.assertEqual(rows[0]["prematch_known"], "NO")
        self.assertEqual(rows[0]["impact_score"], "")
        self.assertIn("NOT_AUTHORIZED", rows[0]["impact_authority"])

    def test_rotation_materializes_structural_change_only(self):
        first = self.xi(1)
        second_list = [
            {"player": {"id": i, "name": f"P{i}"}}
            for i in range(2, 13)
        ]
        rows = p.build_rotation_rows([
            {
                "fixture_id": "1",
                "kickoff_utc": "2025-01-01T12:00:00Z",
                "team_id": "7",
                "team_name": "Team",
                "starting_xi_json": first,
            },
            {
                "fixture_id": "2",
                "kickoff_utc": "2025-01-08T12:00:00Z",
                "team_id": "7",
                "team_name": "Team",
                "starting_xi_json": json.dumps(second_list),
            },
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["retained_starters"], 10)
        self.assertEqual(rows[0]["changed_in_count"], 1)
        self.assertEqual(rows[0]["changed_out_count"], 1)
        self.assertEqual(rows[0]["quality_delta"], "")
        self.assertEqual(
            rows[0]["quality_delta_status"],
            "BLOCKED_UNTIL_STRICTLY_PRIOR_PLAYER_QUALITY_JOIN",
        )

    def test_readiness_separates_components_and_forbids_betting_authority(self):
        readiness = p.build_readiness(
            grade_rows=[{"x": "1"}],
            form_rows=[{"x": "1"}],
            importance_rows=[],
            availability_rows=[{"x": "1"}],
            rotation_rows=[{"x": "1"}],
            international_rows=[{"x": "1"}],
            stage77_meta={"status": "OK", "remaining_unattempted_or_retryable": 100},
            stage78_meta={"leakage_violations": 0, "no_lookahead": True},
        )
        self.assertEqual(readiness["status"], "VALIDATION_PENDING")
        self.assertFalse(readiness["operational_betting_authority"])
        self.assertEqual(
            readiness["components"]["SEPARATION_AND_DOUBLE_COUNTING_GUARD"]["status"],
            "OPERATIONAL_AUTHORIZED",
        )
        self.assertEqual(
            readiness["components"]["AVAILABILITY"]["status"],
            "RESEARCH_ONLY",
        )
        self.assertIn(
            "double_counting_rule",
            readiness["separation_contract"],
        )


if __name__ == "__main__":
    unittest.main()
