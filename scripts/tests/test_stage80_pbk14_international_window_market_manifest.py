import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_manifest as manifest


class PBK14InternationalWindowMarketManifestTests(unittest.TestCase):
    def test_manifest_contract_for_international_window_market_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "pbk14_international_window_market_join_research.csv"
            fields = [
                "historical_match_id",
                "date_iso",
                "api_fixture_id",
                "player_level_international_status",
            ]
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "historical_match_id": "hist-1",
                    "date_iso": "2024-09-14",
                    "api_fixture_id": "9001",
                    "player_level_international_status": "UNVERIFIED",
                })

            report = manifest.build_manifest(root, raw_archive_dir="")

        dataset = next(
            row for row in report["datasets"]
            if row["dataset_id"] == "pbk14_international_window_market_join_research"
        )
        self.assertEqual(dataset["contract_status"], "OK")
        self.assertEqual(dataset["role"], "RESEARCH_JOIN")
        self.assertEqual(
            dataset["lifecycle"],
            "DETERMINISTIC_CALENDAR_CONTEXT_JOIN",
        )
        self.assertEqual(dataset["identity_key_text"], "historical_match_id")
        self.assertEqual(dataset["effective_time_fields_text"], "date_iso")
        self.assertIn("UNVERIFIED", dataset["limitations"])
        self.assertIn("call-up", dataset["limitations"])


if __name__ == "__main__":
    unittest.main()
