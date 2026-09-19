import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_manifest as manifest


class PBK16InternationalWindowManifestTests(unittest.TestCase):
    def test_manifest_contract_for_international_window_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "pbk16_international_window_context_research.csv"
            fields = [
                "domestic_fixture_id",
                "kickoff_utc",
                "player_level_international_status",
                "calendar_level_only",
                "no_lookahead",
            ]
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "domestic_fixture_id": "100",
                    "kickoff_utc": "2025-09-12T15:00:00Z",
                    "player_level_international_status": "UNVERIFIED",
                    "calendar_level_only": "true",
                    "no_lookahead": "true",
                })

            report = manifest.build_manifest(root, raw_archive_dir="")

        dataset = next(
            row for row in report["datasets"]
            if row["dataset_id"] == "pbk16_international_window_context_research"
        )
        self.assertEqual(dataset["contract_status"], "OK")
        self.assertEqual(dataset["role"], "RESEARCH_ENRICHMENT")
        self.assertEqual(
            dataset["lifecycle"],
            "DETERMINISTIC_CALENDAR_CONTEXT_PROJECTION",
        )
        self.assertEqual(dataset["identity_key_text"], "domestic_fixture_id")
        self.assertEqual(dataset["effective_time_fields_text"], "kickoff_utc")
        self.assertIn("Does not infer player call-up", dataset["limitations"])


if __name__ == "__main__":
    unittest.main()
