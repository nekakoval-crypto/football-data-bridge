import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_transfer_source_audit import validate


class Stage80TransferSourceAuditTests(unittest.TestCase):
    def test_accepts_expected_transfer_schema(self):
        metadata = {
            "resources": [{
                "name": "transfers",
                "path": "transfers.csv",
                "format": "csv",
                "schema": {"fields": [
                    {"name": "player_id"},
                    {"name": "player_name"},
                    {"name": "transfer_date"},
                    {"name": "transfer_season"},
                    {"name": "from_club_id"},
                    {"name": "to_club_id"},
                    {"name": "from_club_name"},
                    {"name": "to_club_name"},
                    {"name": "transfer_fee"},
                    {"name": "market_value_in_eur"},
                ]},
            }]
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dataset-metadata.json"
            p.write_text(json.dumps(metadata), encoding="utf-8")
            report = validate(p)
        self.assertEqual(report["status"], "OK")
        self.assertFalse(report["current_operational_authority"])

    def test_reports_missing_fields(self):
        metadata = {"resources": [{"name": "transfers", "schema": {"fields": [{"name": "player_id"}]}}]}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dataset-metadata.json"
            p.write_text(json.dumps(metadata), encoding="utf-8")
            report = validate(p)
        self.assertEqual(report["status"], "ATTENTION")
        self.assertIn("transfer_date", report["missing_fields"])


if __name__ == "__main__":
    unittest.main()
