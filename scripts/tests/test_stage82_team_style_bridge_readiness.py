import unittest

from scripts.stage82_team_style_bridge_readiness import audit_readiness


class Stage82TeamStyleBridgeReadinessTests(unittest.TestCase):

    def _source_row(self, fixture_id, team_id, team_name, side, observed):
        return {
            "fixture_id": str(fixture_id),
            "kickoff_utc": "2026-09-10T18:00:00+00:00",
            "observed_at_utc": observed,
            "team_id": str(team_id),
            "team_name": team_name,
            "side": side,
            "shots_total": "10",
        }

    def test_waiting_when_stage81_source_is_empty(self):
        result = audit_readiness([], [])

        self.assertEqual(result["status"], "WAITING_FOR_STAGE81_DATA")
        self.assertEqual(result["source_rows"], 0)
        self.assertEqual(result["expected_evidence_rows"], 0)
        self.assertEqual(result["provider_calls_added"], 0)

    def test_partial_when_bridge_evidence_is_missing(self):
        source = [
            self._source_row(
                101, 1, "Home FC", "HOME",
                "2026-09-10T20:00:00Z",
            ),
            self._source_row(
                101, 2, "Away FC", "AWAY",
                "2026-09-10T20:00:00Z",
            ),
        ]

        result = audit_readiness(source, [])

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["complete_fixture_pairs"], 1)
        self.assertEqual(result["expected_evidence_rows"], 2)
        self.assertEqual(result["missing_evidence_rows"], 2)
        self.assertEqual(result["coverage_pct"], 0.0)

    def test_ready_when_expected_fixture_team_rows_exist(self):
        source = [
            self._source_row(
                101, 1, "Home FC", "HOME",
                "2026-09-10T20:00:00Z",
            ),
            self._source_row(
                101, 2, "Away FC", "AWAY",
                "2026-09-10T20:00:00Z",
            ),
        ]

        evidence = [
            {
                "fixture_id": 101,
                "team_id": 1,
                "source": "PBK_STAGE81_TEAM_MATCH_STATISTICS",
            },
            {
                "fixture_id": 101,
                "team_id": 2,
                "source": "PBK_STAGE81_TEAM_MATCH_STATISTICS",
            },
        ]

        result = audit_readiness(source, evidence)

        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["missing_evidence_rows"], 0)
        self.assertEqual(result["coverage_pct"], 100.0)

    def test_incomplete_fixture_is_attention_not_ready(self):
        source = [
            self._source_row(
                101, 1, "Home FC", "HOME",
                "2026-09-10T20:00:00Z",
            )
        ]

        result = audit_readiness(source, [])

        self.assertEqual(result["status"], "ATTENTION")
        self.assertEqual(
            result["fixture_pair_exclusions"]["incomplete_fixture_pair"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
