import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_archive_manifest import build_manifest
from scripts.stage80_archive_readiness import build_report


class Stage80PrematchWalkforwardReadinessTests(unittest.TestCase):
    def write_csv(self,path,fields,rows):
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader(); w.writerows(rows)

    def test_missing_walkforward_is_explicit_gap(self):
        with tempfile.TemporaryDirectory() as td:
            report=build_report(Path(td))
            self.assertIn("PREMATCH_FACTOR_WALKFORWARD_NOT_MATERIALIZED",report["gaps"])

    def test_valid_walkforward_is_registered_without_authority(self):
        with tempfile.TemporaryDirectory() as td:
            ops=Path(td)
            fold_fields=[
                "factor","bucket","scope_type","scope_value","target","test_season",
                "train_seasons","research_only","operational_betting_authority",
                "creates_signal","probability_mutation","eligibility_mutation",
                "stake_changes","forward_journal_mutation",
            ]
            summary_fields=[
                "factor","bucket","scope_type","scope_value","target",
                "research_only","operational_betting_authority","creates_signal",
                "promotes_factor","probability_mutation","eligibility_mutation",
                "stake_changes","forward_journal_mutation",
            ]
            self.write_csv(
                ops/"top5_prematch_factor_walkforward_research.csv",fold_fields,
                [{
                    "factor":"WEEKDAY","bucket":"MONDAY","scope_type":"ALL","scope_value":"ALL",
                    "target":"HOME","test_season":"2025/2026","train_seasons":"8",
                    "research_only":"true","operational_betting_authority":"false",
                    "creates_signal":"false","probability_mutation":"false",
                    "eligibility_mutation":"false","stake_changes":"false",
                    "forward_journal_mutation":"false",
                }],
            )
            self.write_csv(
                ops/"top5_prematch_factor_walkforward_summary_research.csv",summary_fields,
                [{
                    "factor":"WEEKDAY","bucket":"MONDAY","scope_type":"ALL","scope_value":"ALL",
                    "target":"HOME","research_only":"true",
                    "operational_betting_authority":"false","creates_signal":"false",
                    "promotes_factor":"false","probability_mutation":"false",
                    "eligibility_mutation":"false","stake_changes":"false",
                    "forward_journal_mutation":"false",
                }],
            )
            meta={
                "version":"PBK_STAGE80_PREMATCH_FACTOR_WALKFORWARD_V1",
                "status":"OK","source_rows":16111,"context_rows":16111,"joined_rows":16111,
                "invalid_context_governance_rows":0,"source_without_context":0,"context_without_source":0,
                "season_labels":[f"{y}/{y+1}" for y in range(2017,2026)],
                "targets":["HOME","DRAW","AWAY","OVER25","UNDER25"],
                "fold_rows":1,"summary_rows":1,"sample_threshold_pass_folds":1,
                "min_prior_seasons":2,"min_train_market_matches":100,"min_test_market_matches":30,
                "provider_calls":0,"research_only":True,
                "operational_betting_authority":False,"creates_signal":False,
                "promotes_factor":False,"probability_mutation":False,
                "eligibility_mutation":False,"stake_changes":False,
                "forward_journal_mutation":False,
            }
            (ops/"stage80_prematch_factor_walkforward_last_run.json").write_text(
                json.dumps(meta),encoding="utf-8"
            )

            report=build_report(ops)
            self.assertNotIn("PREMATCH_FACTOR_WALKFORWARD_NOT_MATERIALIZED",report["gaps"])
            self.assertNotIn("PREMATCH_FACTOR_WALKFORWARD_INVALID_OR_INCOMPLETE",report["gaps"])
            block=report["prematch_factor_walkforward"]
            self.assertEqual(block["valid_fold_rows"],1)
            self.assertEqual(block["valid_summary_rows"],1)
            self.assertFalse(block["operational_betting_authority"])
            self.assertFalse(block["promotes_factor"])

            manifest=build_manifest(ops)
            items={x["dataset_id"]:x for x in manifest["datasets"]}
            self.assertEqual(items["top5_prematch_factor_walkforward_research"]["contract_status"],"OK")
            self.assertEqual(items["top5_prematch_factor_walkforward_summary_research"]["contract_status"],"OK")


if __name__=="__main__":
    unittest.main()
