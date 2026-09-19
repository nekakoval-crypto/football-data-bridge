import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_manifest as manifest
from scripts import stage80_archive_readiness as readiness


class PBK16StandingsFoundationReadinessTests(unittest.TestCase):
    def test_missing_layers_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=readiness.build_report(Path(tmp),archive_dir="")
        self.assertIn("PBK16_DOMESTIC_PHASE_AUDIT_NOT_MATERIALIZED",report["gaps"])
        self.assertIn("PBK16_FORMAT_INVENTORY_NOT_MATERIALIZED",report["gaps"])
        self.assertIn("PBK16_HISTORICAL_TABLE_CONTEXT_NOT_MATERIALIZED",report["gaps"])

    def test_manifest_contracts_for_all_three_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            specs={
                "pbk16_domestic_phase_audit.csv":[
                    "fixture_id","kickoff_utc","phase_role","phase_family",
                    "table_result_policy",
                ],
                "pbk16_domestic_league_format_inventory.csv":[
                    "country","season","structure_class",
                    "exact_motivation_contract_status",
                ],
                "pbk16_historical_table_context_research.csv":[
                    "domestic_fixture_id","kickoff_utc","context_status",
                    "rank_tiebreak_contract","official_table_equivalence",
                ],
            }
            for name,fields in specs.items():
                with (root/name).open("w",encoding="utf-8-sig",newline="") as f:
                    w=csv.DictWriter(f,fieldnames=fields)
                    w.writeheader()
                    row={field:"x" for field in fields}
                    if "fixture_id" in row: row["fixture_id"]="100"
                    if "domestic_fixture_id" in row: row["domestic_fixture_id"]="100"
                    if "kickoff_utc" in row: row["kickoff_utc"]="2025-09-12T15:00:00Z"
                    if "country" in row: row["country"]="England"
                    if "season" in row: row["season"]="2025"
                    w.writerow(row)
            report=manifest.build_manifest(root,raw_archive_dir="")

        by_id={row["dataset_id"]:row for row in report["datasets"]}
        phase=by_id["pbk16_domestic_phase_audit"]
        fmt=by_id["pbk16_domestic_league_format_inventory"]
        table=by_id["pbk16_historical_table_context_research"]

        self.assertEqual(phase["contract_status"],"OK")
        self.assertEqual(phase["identity_key_text"],"fixture_id")
        self.assertEqual(phase["effective_time_fields_text"],"kickoff_utc")
        self.assertEqual(fmt["contract_status"],"OK")
        self.assertEqual(fmt["identity_key_text"],"country+season")
        self.assertIn("UNVERIFIED",fmt["limitations"])
        self.assertEqual(table["contract_status"],"OK")
        self.assertEqual(table["identity_key_text"],"domestic_fixture_id")
        self.assertIn("UNKNOWN_BY_DESIGN",table["limitations"])
        self.assertIn("awarded",table["limitations"].lower())


if __name__=="__main__":
    unittest.main()
