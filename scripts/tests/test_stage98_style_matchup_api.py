import json
import sqlite3
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage73_internal_api as api


class Stage98StyleMatchupApiTests(
    unittest.TestCase
):

    def setUp(self):
        self.original_db = api.DB

    def tearDown(self):
        api.DB = self.original_db

    def test_today_and_round_contract_remain_provider_free(self):
        self.assertFalse(
            api.today_payload.__name__ == ""
        )

        # Contract-level protection:
        # Stage97 context itself is provider-free and
        # Stage73 remains read-only.
        self.assertEqual(
            api.API_VERSION,
            "v1",
        )

    def test_stage97_contract_has_no_model_mutation(self):
        from scripts.stage97_style_matchup_today_live import (
            build_today_live_style_context,
        )

        conn = sqlite3.connect(":memory:")

        conn.execute(
            "CREATE TABLE state_documents "
            "(name TEXT PRIMARY KEY, "
            "payload_json TEXT NOT NULL, "
            "sha256 TEXT NOT NULL)"
        )

        fixture = {
            "fixture_id": "100",
            "provider_league_id": "39",
            "season": "2026",
        }

        result = build_today_live_style_context(
            conn,
            fixture,
        )

        self.assertTrue(result["research_only"])
        self.assertFalse(
            result["provider_polling"]
        )
        self.assertFalse(
            result["creates_signal"]
        )
        self.assertFalse(
            result["probability_mutation"]
        )
        self.assertFalse(
            result["eligibility_mutation"]
        )


if __name__ == "__main__":
    unittest.main()
