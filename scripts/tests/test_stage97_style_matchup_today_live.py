import json
import sqlite3
import unittest

from scripts.stage97_style_matchup_today_live import (
    build_today_live_style_context,
)


class Stage97StyleMatchupTodayLiveTests(
    unittest.TestCase
):

    def conn(self):
        conn = sqlite3.connect(":memory:")

        conn.execute(
            "CREATE TABLE state_documents "
            "(name TEXT PRIMARY KEY, "
            "payload_json TEXT NOT NULL, "
            "sha256 TEXT NOT NULL)"
        )

        return conn

    def put(self, conn, name, payload):
        conn.execute(
            "INSERT INTO state_documents "
            "VALUES (?,?,?)",
            (
                name,
                json.dumps(payload),
                "test",
            ),
        )

    def fixture(self):
        return {
            "fixture_id": "100",
            "provider_league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "kickoff_utc": (
                "2026-09-18T18:00:00Z"
            ),
        }

    def test_missing_data_is_honestly_waiting(self):
        result = build_today_live_style_context(
            self.conn(),
            self.fixture(),
        )

        self.assertFalse(result["available"])
        self.assertEqual(
            result["style_status"],
            "DATA_WAITING",
        )
        self.assertEqual(
            result["matchup_status"],
            "DATA_WAITING",
        )

    def test_research_context_never_authorizes_grade_or_probability(self):
        conn = self.conn()

        self.put(
            conn,
            "matchup_validation_gate.json",
            {
                "version": (
                    "PBK_STAGE95_MATCHUP_VALIDATION_GATE_V1"
                ),
                "status": "DATA_BLOCKED",
                "components_with_required_evidence": 0,
                "total_components": 7,
            },
        )

        result = build_today_live_style_context(
            conn,
            self.fixture(),
        )

        self.assertEqual(
            result["matchup_status"],
            "DATA_BLOCKED",
        )
        self.assertFalse(
            result["matchup_grade_authorized"]
        )
        self.assertFalse(
            result["probability_mutation"]
        )
        self.assertFalse(
            result["eligibility_mutation"]
        )

    def test_style_evidence_is_exposed_without_validation_claim(self):
        conn = self.conn()

        self.put(
            conn,
            "team_style_dimension_validation_statistics.json",
            {
                "version": (
                    "PBK_STAGE94_STYLE_DIMENSION_VALIDATION_STATISTICS_V1"
                ),
                "groups": [
                    {
                        "league_id": "39",
                        "season": "2026",
                        "dimension": "ATTACK_VOLUME",
                        "validation_status": (
                            "VALIDATION_EVIDENCE_AVAILABLE"
                        ),
                    }
                ],
            },
        )

        result = build_today_live_style_context(
            conn,
            self.fixture(),
        )

        self.assertEqual(
            result["style_status"],
            "VALIDATION_EVIDENCE_AVAILABLE",
        )
        self.assertEqual(
            result[
                "validation_evidence_dimensions"
            ],
            ["ATTACK_VOLUME"],
        )
        self.assertFalse(
            result[
                "validated_style_claim_allowed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
