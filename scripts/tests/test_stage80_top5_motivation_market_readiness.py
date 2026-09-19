import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_archive_manifest import build_manifest
from scripts.stage80_archive_readiness import build_report


FACTORS=[
    "PRESSURE_ASYMMETRY","HIGH_PRESSURE_SIDE","MEDIUM_HIGH_PRESSURE_SIDE",
    "LATE_TITLE_NEAR_3_SIDE","LATE_TITLE_NEAR_6_SIDE",
    "LATE_SURVIVAL_DANGER_SIDE","LATE_SURVIVAL_WITHIN_3_SIDE",
    "LATE_SURVIVAL_WITHIN_6_SIDE","DRAW_TITLE_PATH_SIDE","DRAW_SAFE_PATH_SIDE",
]


class Top5MotivationMarketResearchReadinessTests(unittest.TestCase):
    def write_csv(self,path,fields,rows):
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader(); w.writerows(rows)

    def materialize(self,ops: Path,*,promotes=False):
        profile={
            "factor":"HIGH_PRESSURE_SIDE","bucket":"HOME_ONLY",
            "scope_type":"ALL","scope_value":"ALL","matches":"250",
            "research_only":"true","operational_betting_authority":"false",
            "creates_signal":"false","probability_mutation":"false",
            "eligibility_mutation":"false","stake_changes":"false",
            "forward_journal_mutation":"false",
        }
        stability={
            "factor":"HIGH_PRESSURE_SIDE","bucket":"HOME_ONLY",
            "scope_type":"ALL","scope_value":"ALL","seasons_with_matches":"9",
            "research_only":"true","operational_betting_authority":"false",
            "creates_signal":"false",
        }
        self.write_csv(
            ops/"top5_motivation_market_factor_research.csv",list(profile),[profile]
        )
        self.write_csv(
            ops/"top5_motivation_market_factor_stability_research.csv",
            list(stability),[stability],
        )
        meta={
            "version":"PBK_STAGE80_TOP5_MOTIVATION_MARKET_RESEARCH_V1",
            "status":"OK",
            "source_rows":16111,"context_rows":16111,
            "source_unique_ids":16111,"context_unique_ids":16111,
            "joined_rows":16111,"invalid_context_governance_rows":0,
            "source_without_context":0,"context_without_source":0,
            "factor_names":FACTORS,
            "factor_profile_rows":1,"season_stability_rows":1,
            "closing_1x2_matches":13000,"closing_total25_matches":10000,
            "motivation_contract":"TOP5_HISTORICAL_MOTIVATION_V1_NO_LOOKAHEAD",
            "rank_tiebreak_contract":"POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1",
            "europe_status":"UNKNOWN_BY_DESIGN",
            "generic_must_win_created":False,"unmotivated_label_created":False,
            "provider_calls":0,"research_only":True,
            "operational_betting_authority":False,"creates_signal":False,
            "promotes_factor":promotes,
            "probability_mutation":False,"eligibility_mutation":False,
            "stake_changes":False,"forward_journal_mutation":False,
        }
        (ops/"stage80_top5_motivation_market_research_last_run.json").write_text(
            json.dumps(meta),encoding="utf-8"
        )

    def test_valid_research_closes_gap_and_manifest_contracts_are_ok(self):
        with tempfile.TemporaryDirectory() as td:
            ops=Path(td)
            self.materialize(ops)
            report=build_report(ops,archive_dir="")
            layer=report["top5_motivation_market_research"]
            self.assertTrue(layer["meta_valid"])
            self.assertEqual(layer["valid_profile_rows"],1)
            self.assertEqual(layer["valid_stability_rows"],1)
            self.assertEqual(layer["europe_status"],"UNKNOWN_BY_DESIGN")
            self.assertFalse(layer["promotes_factor"])
            self.assertNotIn("TOP5_MOTIVATION_MARKET_RESEARCH_NOT_MATERIALIZED",report["gaps"])
            self.assertNotIn("TOP5_MOTIVATION_MARKET_RESEARCH_INVALID_OR_INCOMPLETE",report["gaps"])

            manifest=build_manifest(ops,raw_archive_dir="")
            by_id={x["dataset_id"]:x for x in manifest["datasets"]}
            self.assertEqual(
                by_id["top5_motivation_market_factor_research"]["contract_status"],"OK"
            )
            self.assertEqual(
                by_id["top5_motivation_market_factor_stability_research"]["contract_status"],"OK"
            )
            self.assertIn(
                "UNKNOWN_BY_DESIGN",
                by_id["top5_motivation_market_factor_research"]["limitations"],
            )

    def test_promotion_leak_invalidates_research(self):
        with tempfile.TemporaryDirectory() as td:
            ops=Path(td)
            self.materialize(ops,promotes=True)
            report=build_report(ops,archive_dir="")
            self.assertIn("TOP5_MOTIVATION_MARKET_RESEARCH_INVALID_OR_INCOMPLETE",report["gaps"])

    def test_missing_research_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            report=build_report(Path(td),archive_dir="")
            self.assertIn("TOP5_MOTIVATION_MARKET_RESEARCH_NOT_MATERIALIZED",report["gaps"])


if __name__=="__main__":
    unittest.main()
