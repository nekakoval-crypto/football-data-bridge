import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_manifest as manifest


class PBK14InternationalWindowMarketResearchManifestTests(unittest.TestCase):
    def test_manifest_contracts_for_profiles_and_stability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            files={
                "pbk14_international_window_market_factor_research.csv":[
                    "factor","bucket","scope_type","scope_value","matches","promotes_factor"
                ],
                "pbk14_international_window_market_factor_stability_research.csv":[
                    "factor","bucket","scope_type","scope_value","seasons_with_matches","promotes_factor"
                ],
            }
            for name,fields in files.items():
                with (root/name).open("w",encoding="utf-8-sig",newline="") as f:
                    w=csv.DictWriter(f,fieldnames=fields)
                    w.writeheader()
                    w.writerow({
                        **{field:"x" for field in fields},
                        "factor":"INTL_AFTER_72H",
                        "bucket":"WITHIN",
                        "scope_type":"ALL",
                        "scope_value":"ALL",
                        "promotes_factor":"false",
                    })

            report=manifest.build_manifest(root,raw_archive_dir="")

        by_id={row["dataset_id"]:row for row in report["datasets"]}
        profile=by_id["pbk14_international_window_market_factor_research"]
        stability=by_id["pbk14_international_window_market_factor_stability_research"]
        self.assertEqual(profile["contract_status"],"OK")
        self.assertEqual(profile["role"],"RESEARCH_ANALYSIS")
        self.assertEqual(profile["identity_key_text"],"factor+bucket+scope_type+scope_value")
        self.assertIn("player duty remains UNVERIFIED",profile["limitations"])
        self.assertEqual(stability["contract_status"],"OK")
        self.assertEqual(stability["role"],"RESEARCH_VALIDATION")
        self.assertIn("call-up",stability["limitations"])


if __name__=="__main__":
    unittest.main()
