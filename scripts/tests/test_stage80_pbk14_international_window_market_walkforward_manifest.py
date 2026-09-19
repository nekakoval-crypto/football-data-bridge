import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_manifest as manifest


class PBK14InternationalWindowMarketWalkforwardManifestTests(unittest.TestCase):
    def test_manifest_contracts_for_folds_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            files={
                "pbk14_international_window_market_walkforward_research.csv":[
                    "factor","bucket","scope_type","scope_value","target","test_season"
                ],
                "pbk14_international_window_market_walkforward_summary_research.csv":[
                    "factor","bucket","scope_type","scope_value","target",
                    "first_test_season","last_test_season"
                ],
            }
            for name,fields in files.items():
                with (root/name).open("w",encoding="utf-8-sig",newline="") as f:
                    w=csv.DictWriter(f,fieldnames=fields)
                    w.writeheader()
                    row={field:"x" for field in fields}
                    row.update({
                        "factor":"INTL_BEFORE_72H",
                        "bucket":"WITHIN",
                        "scope_type":"ALL",
                        "scope_value":"ALL",
                        "target":"HOME",
                    })
                    if "test_season" in fields:
                        row["test_season"]="2024"
                    if "first_test_season" in fields:
                        row["first_test_season"]="2019"
                        row["last_test_season"]="2025"
                    w.writerow(row)

            report=manifest.build_manifest(root,raw_archive_dir="")

        by_id={row["dataset_id"]:row for row in report["datasets"]}
        folds=by_id["pbk14_international_window_market_walkforward_research"]
        summary=by_id["pbk14_international_window_market_walkforward_summary_research"]
        self.assertEqual(folds["contract_status"],"OK")
        self.assertEqual(folds["role"],"RESEARCH_VALIDATION")
        self.assertEqual(
            folds["identity_key_text"],
            "factor+bucket+scope_type+scope_value+target+test_season",
        )
        self.assertIn("player duty remains UNVERIFIED",folds["limitations"])
        self.assertEqual(summary["contract_status"],"OK")
        self.assertEqual(summary["role"],"RESEARCH_VALIDATION")
        self.assertIn("call-up",summary["limitations"])


if __name__=="__main__":
    unittest.main()
