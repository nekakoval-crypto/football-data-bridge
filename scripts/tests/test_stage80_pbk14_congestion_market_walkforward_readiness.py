import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_readiness as readiness


class PBK14CongestionWalkforwardReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.ops=Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self,name,fields,rows):
        with (self.ops/name).open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader(); w.writerows(rows)

    def write_json(self,name,payload):
        (self.ops/name).write_text(
            json.dumps(payload,ensure_ascii=False,indent=2),
            encoding="utf-8",
        )

    def materialize_join(self):
        join={
            "historical_match_id":"hist-1","api_fixture_id":"9001",
            "mapping_status":"AUTO","league_code":"E0","season_start":"2024",
            "date_iso":"2024-08-10","fuzzy_string_matching_used":"false",
            "one_to_one_verified":"true","strictly_prior_fixture_evidence_only":"true",
            "future_schedule_used":"false","no_lookahead":"true",
            "historical_backfill_only":"true","research_only":"true",
            "operational_betting_authority":"false","creates_signal":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        }
        self.write_csv("pbk14_congestion_market_join_research.csv",list(join),[join])
        self.write_json(
            "stage80_pbk14_congestion_market_join_last_run.json",
            {
                "version":"PBK_STAGE80_PBK14_CONGESTION_MARKET_JOIN_V1",
                "joined_rows":1,"missing_market_rows":0,"missing_congestion_rows":0,
                "bridge_eligible_duplicate_historical_ids":0,
                "bridge_eligible_duplicate_api_fixture_ids":0,
                "congestion_duplicate_fixture_ids":0,
                "join_coverage_pct":100.0,
                "review_unmapped_excluded":True,"fuzzy_string_matching_used":False,
                "strictly_prior_fixture_evidence_only":True,
                "future_schedule_used":False,"no_lookahead":True,
                "provider_calls":0,"research_only":True,
                "operational_betting_authority":False,"creates_signal":False,
                "probability_mutation":False,"eligibility_mutation":False,
                "stake_changes":False,"forward_journal_mutation":False,
            },
        )

    def materialize_walkforward(self,temporal_ok=True,promotes=False):
        fold={
            "factor":"UEFA_72H_SIDE","bucket":"HOME_ONLY",
            "scope_type":"ALL","scope_value":"ALL","target":"HOME",
            "test_season":"2024","train_first_season":"2022",
            "train_last_season":"2023" if temporal_ok else "2024",
            "train_seasons":"2","train_market_matches":"100",
            "test_market_matches":"30","sample_threshold_pass":"true",
            "research_only":"true","operational_betting_authority":"false",
            "creates_signal":"false","promotes_factor":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        }
        summary={
            "factor":"UEFA_72H_SIDE","bucket":"HOME_ONLY",
            "scope_type":"ALL","scope_value":"ALL","target":"HOME",
            "folds":"1","sample_threshold_pass_folds":"1",
            "research_only":"true","operational_betting_authority":"false",
            "creates_signal":"false","promotes_factor":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        }
        self.write_csv("pbk14_congestion_market_walkforward_research.csv",list(fold),[fold])
        self.write_csv("pbk14_congestion_market_walkforward_summary_research.csv",list(summary),[summary])
        factors=[
            "NONLEAGUE_72H_SIDE","NONLEAGUE_96H_SIDE",
            "UEFA_72H_SIDE","UEFA_96H_SIDE",
            "DOMESTIC_CUP_72H_SIDE","DOMESTIC_CUP_96H_SIDE",
            "PREV_NONLEAGUE_THURSDAY_SIDE","THURSDAY_TO_WEEKEND_SIDE",
        ]
        self.write_json(
            "stage80_pbk14_congestion_market_walkforward_last_run.json",
            {
                "version":"PBK_STAGE80_PBK14_CONGESTION_MARKET_WALKFORWARD_V1",
                "status":"OK","source_rows":1,"valid_research_rows":1,
                "invalid_governance_or_result_rows":0,
                "season_starts":["2017","2018","2019","2020","2021","2022","2023","2024","2025"],
                "factor_names":factors,
                "targets":["HOME","DRAW","AWAY","OVER25","UNDER25"],
                "fold_rows":1,"summary_rows":1,"sample_threshold_pass_folds":1,
                "min_prior_seasons":2,"min_train_market_matches":100,"min_test_market_matches":30,
                "strictly_prior_fixture_evidence_only":True,
                "future_schedule_used":False,"no_lookahead":True,"provider_calls":0,
                "research_only":True,"operational_betting_authority":False,
                "creates_signal":False,"promotes_factor":promotes,
                "probability_mutation":False,"eligibility_mutation":False,
                "stake_changes":False,"forward_journal_mutation":False,
            },
        )

    def test_valid_walkforward_closes_gap(self):
        self.materialize_join()
        self.materialize_walkforward()
        report=readiness.build_report(self.ops,archive_dir="")
        wf=report["pbk14_congestion_market_walkforward"]
        self.assertTrue(wf["meta_valid"])
        self.assertEqual(wf["valid_fold_rows"],1)
        self.assertEqual(wf["temporal_invalid_rows"],0)
        self.assertFalse(wf["promotes_factor"])
        self.assertNotIn("PBK14_CONGESTION_MARKET_WALKFORWARD_NOT_MATERIALIZED",report["gaps"])
        self.assertNotIn("PBK14_CONGESTION_MARKET_WALKFORWARD_INVALID",report["gaps"])

    def test_temporal_leak_is_invalid(self):
        self.materialize_join()
        self.materialize_walkforward(temporal_ok=False)
        report=readiness.build_report(self.ops,archive_dir="")
        self.assertIn("PBK14_CONGESTION_MARKET_WALKFORWARD_INVALID",report["gaps"])
        self.assertEqual(report["pbk14_congestion_market_walkforward"]["temporal_invalid_rows"],1)

    def test_promotion_leak_is_invalid(self):
        self.materialize_join()
        self.materialize_walkforward(promotes=True)
        report=readiness.build_report(self.ops,archive_dir="")
        self.assertIn("PBK14_CONGESTION_MARKET_WALKFORWARD_INVALID",report["gaps"])

    def test_missing_walkforward_is_explicit(self):
        self.materialize_join()
        report=readiness.build_report(self.ops,archive_dir="")
        self.assertIn("PBK14_CONGESTION_MARKET_WALKFORWARD_NOT_MATERIALIZED",report["gaps"])


if __name__=="__main__":
    unittest.main()
