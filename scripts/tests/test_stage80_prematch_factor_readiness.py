import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_archive_manifest import build_manifest
from scripts.stage80_archive_readiness import build_report


class Stage80PrematchFactorReadinessTests(unittest.TestCase):
    def write_csv(self,path,fieldnames,rows):
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fieldnames)
            w.writeheader(); w.writerows(rows)

    def test_missing_factor_research_is_explicit_gap(self):
        with tempfile.TemporaryDirectory() as td:
            report=build_report(Path(td))
            self.assertIn("PREMATCH_FACTOR_RESEARCH_NOT_MATERIALIZED",report["gaps"])

    def test_materialized_factor_research_is_valid_and_registered(self):
        with tempfile.TemporaryDirectory() as td:
            ops=Path(td)
            profile_fields=[
                "factor","bucket","scope_type","scope_value","matches",
                "research_only","operational_betting_authority","creates_signal",
                "probability_mutation","eligibility_mutation","stake_changes","forward_journal_mutation",
            ]
            stability_fields=[
                "factor","bucket","scope_type","scope_value","seasons_with_matches",
                "research_only","operational_betting_authority","creates_signal",
            ]
            self.write_csv(
                ops/"top5_prematch_factor_research.csv",profile_fields,
                [{
                    "factor":"WEEKDAY","bucket":"MONDAY","scope_type":"ALL","scope_value":"ALL",
                    "matches":"100","research_only":"true","operational_betting_authority":"false",
                    "creates_signal":"false","probability_mutation":"false",
                    "eligibility_mutation":"false","stake_changes":"false",
                    "forward_journal_mutation":"false",
                }],
            )
            self.write_csv(
                ops/"top5_prematch_factor_stability_research.csv",stability_fields,
                [{
                    "factor":"WEEKDAY","bucket":"MONDAY","scope_type":"ALL","scope_value":"ALL",
                    "seasons_with_matches":"9","research_only":"true",
                    "operational_betting_authority":"false","creates_signal":"false",
                }],
            )
            meta={
                "version":"PBK_STAGE80_PREMATCH_FACTOR_RESEARCH_V1",
                "status":"OK",
                "source_rows":16111,"context_rows":16111,"joined_rows":16111,
                "invalid_context_governance_rows":0,"source_without_context":0,"context_without_source":0,
                "factor_names":[
                    "WEEKDAY","KICKOFF_LOCAL","SHORT_REST","REST_ADVANTAGE",
                    "CONGESTION_7D_DIFF","TABLE_RANK_DIFF","FORM5_PPG_DIFF","VENUE_FORM5_PPG_DIFF"
                ],
                "factor_profile_rows":1,"season_stability_rows":1,
                "closing_1x2_matches":10000,"closing_total25_matches":9000,
                "provider_calls":0,"research_only":True,
                "operational_betting_authority":False,"creates_signal":False,
                "probability_mutation":False,"eligibility_mutation":False,
                "stake_changes":False,"forward_journal_mutation":False,
            }
            (ops/"stage80_prematch_factor_research_last_run.json").write_text(
                json.dumps(meta),encoding="utf-8"
            )
            report=build_report(ops)
            self.assertNotIn("PREMATCH_FACTOR_RESEARCH_NOT_MATERIALIZED",report["gaps"])
            self.assertNotIn("PREMATCH_FACTOR_RESEARCH_INVALID_OR_INCOMPLETE",report["gaps"])
            block=report["prematch_factor_research"]
            self.assertEqual(block["valid_profile_rows"],1)
            self.assertEqual(block["valid_stability_rows"],1)
            self.assertFalse(block["operational_betting_authority"])

            manifest=build_manifest(ops)
            by_id={item["dataset_id"]:item for item in manifest["datasets"]}
            self.assertEqual(by_id["top5_prematch_factor_research"]["contract_status"],"OK")
            self.assertEqual(by_id["top5_prematch_factor_stability_research"]["contract_status"],"OK")


if __name__=="__main__":
    unittest.main()
