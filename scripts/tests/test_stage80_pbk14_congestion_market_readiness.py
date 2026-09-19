import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_readiness as readiness


class PBK14CongestionMarketReadinessTests(unittest.TestCase):
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

    def materialize_join_and_research(self):
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
        self.write_csv(
            "pbk14_congestion_market_join_research.csv",
            list(join),
            [join],
        )
        self.write_json(
            "stage80_pbk14_congestion_market_join_last_run.json",
            {
                "version":"PBK_STAGE80_PBK14_CONGESTION_MARKET_JOIN_V1",
                "joined_rows":1,
                "missing_market_rows":0,
                "missing_congestion_rows":0,
                "bridge_eligible_duplicate_historical_ids":0,
                "bridge_eligible_duplicate_api_fixture_ids":0,
                "congestion_duplicate_fixture_ids":0,
                "join_coverage_pct":100.0,
                "review_unmapped_excluded":True,
                "fuzzy_string_matching_used":False,
                "strictly_prior_fixture_evidence_only":True,
                "future_schedule_used":False,
                "no_lookahead":True,
                "provider_calls":0,
                "research_only":True,
                "operational_betting_authority":False,
                "creates_signal":False,
                "probability_mutation":False,
                "eligibility_mutation":False,
                "stake_changes":False,
                "forward_journal_mutation":False,
            },
        )

        profile={
            "factor":"UEFA_72H_SIDE","bucket":"HOME_ONLY",
            "scope_type":"ALL","scope_value":"ALL","matches":"1",
            "research_only":"true","operational_betting_authority":"false",
            "creates_signal":"false","promotes_factor":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        }
        stability={
            "factor":"UEFA_72H_SIDE","bucket":"HOME_ONLY",
            "scope_type":"ALL","scope_value":"ALL","seasons_with_matches":"1",
            "research_only":"true","operational_betting_authority":"false",
            "creates_signal":"false","promotes_factor":"false",
        }
        self.write_csv(
            "pbk14_congestion_market_factor_research.csv",
            list(profile),
            [profile],
        )
        self.write_csv(
            "pbk14_congestion_market_factor_stability_research.csv",
            list(stability),
            [stability],
        )
        self.write_json(
            "stage80_pbk14_congestion_market_research_last_run.json",
            {
                "version":"PBK_STAGE80_PBK14_CONGESTION_MARKET_RESEARCH_V1",
                "source_rows":1,
                "valid_research_rows":1,
                "invalid_governance_or_result_rows":0,
                "factor_names":[
                    "NONLEAGUE_72H_SIDE","NONLEAGUE_96H_SIDE",
                    "UEFA_72H_SIDE","UEFA_96H_SIDE",
                    "DOMESTIC_CUP_72H_SIDE","DOMESTIC_CUP_96H_SIDE",
                    "PREV_NONLEAGUE_THURSDAY_SIDE","THURSDAY_TO_WEEKEND_SIDE",
                ],
                "factor_profile_rows":1,
                "stability_rows":1,
                "closing_1x2_matches":1,
                "closing_total25_matches":1,
                "market_novig_is_pbk_probability":False,
                "strictly_prior_fixture_evidence_only":True,
                "future_schedule_used":False,
                "no_lookahead":True,
                "provider_calls":0,
                "research_only":True,
                "operational_betting_authority":False,
                "creates_signal":False,
                "promotes_factor":False,
                "probability_mutation":False,
                "eligibility_mutation":False,
                "stake_changes":False,
                "forward_journal_mutation":False,
            },
        )

    def test_complete_materialization_closes_join_and_research_gaps(self):
        self.materialize_join_and_research()
        report=readiness.build_report(self.ops,archive_dir="")
        layer=report["pbk14_congestion_market_research"]
        self.assertTrue(layer["join_meta_valid"])
        self.assertTrue(layer["research_meta_valid"])
        self.assertEqual(layer["valid_join_rows"],1)
        self.assertEqual(layer["valid_profile_rows"],1)
        self.assertEqual(layer["valid_stability_rows"],1)
        self.assertFalse(layer["promotes_factor"])
        self.assertNotIn("PBK14_CONGESTION_MARKET_JOIN_NOT_MATERIALIZED",report["gaps"])
        self.assertNotIn("PBK14_CONGESTION_MARKET_JOIN_INVALID",report["gaps"])
        self.assertNotIn("PBK14_CONGESTION_MARKET_RESEARCH_NOT_MATERIALIZED",report["gaps"])
        self.assertNotIn("PBK14_CONGESTION_MARKET_RESEARCH_INVALID",report["gaps"])

    def test_missing_materialization_is_explicit(self):
        report=readiness.build_report(self.ops,archive_dir="")
        self.assertIn("PBK14_CONGESTION_MARKET_JOIN_NOT_MATERIALIZED",report["gaps"])
        self.assertIn("PBK14_CONGESTION_MARKET_RESEARCH_NOT_MATERIALIZED",report["gaps"])

    def test_promotion_leak_invalidates_research(self):
        self.materialize_join_and_research()
        p=json.loads((self.ops/"stage80_pbk14_congestion_market_research_last_run.json").read_text())
        p["promotes_factor"]=True
        self.write_json("stage80_pbk14_congestion_market_research_last_run.json",p)
        report=readiness.build_report(self.ops,archive_dir="")
        self.assertIn("PBK14_CONGESTION_MARKET_RESEARCH_INVALID",report["gaps"])


if __name__=="__main__":
    unittest.main()
