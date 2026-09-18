import json
import sqlite3
import unittest

from scripts.style_matchup_passport import (
    build_style_matchup_passport,
)


class Stage96StyleMatchupPassportTests(
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

    def test_missing_documents_remain_data_waiting(self):
        conn = self.conn()

        result = build_style_matchup_passport(
            conn,
            self.fixture(),
        )

        self.assertFalse(
            result["available"]
        )
        self.assertEqual(
            result["style_validation"]["status"],
            "DATA_WAITING",
        )
        self.assertEqual(
            result["matchup_validation"]["status"],
            "DATA_WAITING",
        )

    def test_only_fixture_league_and_season_are_exposed(self):
        conn = self.conn()

        self.put(
            conn,
            "team_style_validation_readiness.json",
            {
                "version": (
                    "PBK_STAGE93_STYLE_VALIDATION_READINESS_V1"
                ),
                "groups": [
                    {
                        "league_id": "39",
                        "season": "2026",
                        "dimension": "ATTACK_VOLUME",
                        "readiness_status": "READY",
                    },
                    {
                        "league_id": "140",
                        "season": "2026",
                        "dimension": "POSSESSION_CONTROL",
                        "readiness_status": "READY",
                    },
                ],
            },
        )

        result = build_style_matchup_passport(
            conn,
            self.fixture(),
        )

        self.assertEqual(
            result["style_validation"][
                "ready_dimensions"
            ],
            ["ATTACK_VOLUME"],
        )

    def test_matchup_gate_is_context_only(self):
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

        result = build_style_matchup_passport(
            conn,
            self.fixture(),
        )

        self.assertTrue(result["available"])

        self.assertEqual(
            result["matchup_validation"]["status"],
            "DATA_BLOCKED",
        )

        self.assertFalse(
            result["matchup_validation"][
                "matchup_grade_authorized"
            ]
        )

        self.assertFalse(
            result["probability_mutation"]
        )
        self.assertFalse(
            result["eligibility_mutation"]
        )


if __name__ == "__main__":
    unittest.main()
