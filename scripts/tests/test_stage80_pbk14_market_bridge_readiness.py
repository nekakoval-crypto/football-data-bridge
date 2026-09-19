import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_readiness as readiness


class PBK14MarketBridgeReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.ops=Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self,name,fields,rows):
        with (self.ops/name).open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    def write_json(self,name,payload):
        (self.ops/name).write_text(
            json.dumps(payload,ensure_ascii=False,indent=2),
            encoding="utf-8",
        )

    def materialize(self,status="AUTO"):
        row={
            "historical_match_id":"hist-1",
            "league_code":"E0",
            "provider_league_id":"39",
            "season_start":"2024",
            "date_iso":"2024-08-10",
            "source_home_team":"Arsenal",
            "source_away_team":"Chelsea",
            "source_home_goals":"2",
            "source_away_goals":"1",
            "api_fixture_id":"9001" if status in {"AUTO","HIGH"} else "",
            "api_kickoff_utc":"2024-08-10T15:00:00+00:00" if status in {"AUTO","HIGH"} else "",
            "api_home_team_id":"42" if status in {"AUTO","HIGH"} else "",
            "api_home_team":"Arsenal" if status in {"AUTO","HIGH"} else "",
            "api_away_team_id":"49" if status in {"AUTO","HIGH"} else "",
            "api_away_team":"Chelsea" if status in {"AUTO","HIGH"} else "",
            "api_home_goals":"2" if status in {"AUTO","HIGH"} else "",
            "api_away_goals":"1" if status in {"AUTO","HIGH"} else "",
            "home_team_map_status":"AUTO",
            "home_team_map_method":"CANONICAL_EXACT",
            "away_team_map_status":"AUTO",
            "away_team_map_method":"CANONICAL_EXACT",
            "mapping_status":status,
            "mapping_reason":"EXACT_DATE_TEAMS_SCORE_UNIQUE" if status in {"AUTO","HIGH"} else "TEAM_IDENTITY_INCOMPLETE",
            "exact_date_required":"true",
            "final_score_identity_evidence":"true",
            "fuzzy_string_matching_used":"false",
            "one_to_one_verified":"true" if status in {"AUTO","HIGH"} else "false",
            "historical_backfill_only":"true",
            "research_only":"true",
            "operational_betting_authority":"false",
            "creates_signal":"false",
            "probability_mutation":"false",
            "eligibility_mutation":"false",
            "stake_changes":"false",
            "forward_journal_mutation":"false",
        }
        self.write_csv(
            "pbk14_football_data_fixture_bridge.csv",
            list(row),
            [row],
        )
        self.write_json(
            "stage80_football_data_pbk14_history_last_run.json",
            {
                "version":"PBK_STAGE80_FOOTBALL_DATA_PBK14_HISTORY_V1",
                "expected_source_files":94,
                "present_source_files":94,
                "missing_source_files":0,
                "supported_leagues":14,
                "unsupported_pbk_leagues":[
                    {"country":"Lithuania","league_name":"A Lyga","provider_league_id":362,"reason":"NO_FOOTBALL_DATA_HISTORICAL_MARKET_SOURCE"},
                    {"country":"Latvia","league_name":"Virsliga","provider_league_id":365,"reason":"NO_FOOTBALL_DATA_HISTORICAL_MARKET_SOURCE"},
                ],
                "historical_backfill_only":True,
                "research_only":True,
                "operational_betting_authority":False,
                "creates_signal":False,
                "probability_mutation":False,
                "eligibility_mutation":False,
                "stake_changes":False,
                "forward_journal_mutation":False,
            },
        )
        counts={"AUTO":0,"HIGH":0,"REVIEW":0,"UNMAPPED":0}
        counts[status]=1
        self.write_json(
            "stage80_pbk14_fixture_bridge_last_run.json",
            {
                "version":"PBK_STAGE80_PBK14_FIXTURE_BRIDGE_V2_NEAR_COMPLETE",
                "source_rows":1,
                "mapped_auto":counts["AUTO"],
                "mapped_high":counts["HIGH"],
                "mapped_auto_high":counts["AUTO"]+counts["HIGH"],
                "review":counts["REVIEW"],
                "unmapped":counts["UNMAPPED"],
                "duplicate_mapped_api_fixture_ids":0,
                "mapping_policy":{
                    "fuzzy_string_matching_used":False,
                    "review_unmapped_excluded":True,
                    "final_score_identity_only":True,
                    "source_aliases_may_share_provider_team_if_fixture_evidence_is_disjoint":True,
                    "near_complete_thresholds":{"min_source_ratio":0.88},
                },
                "historical_backfill_only":True,
                "research_only":True,
                "operational_betting_authority":False,
                "creates_signal":False,
                "probability_mutation":False,
                "eligibility_mutation":False,
                "stake_changes":False,
                "forward_journal_mutation":False,
            },
        )

    def test_auto_materialization_is_valid_and_source_limit_remains_explicit(self):
        self.materialize("AUTO")
        report=readiness.build_report(self.ops,archive_dir="")
        bridge=report["pbk14_historical_market_bridge"]
        self.assertTrue(bridge["source_meta_valid"])
        self.assertTrue(bridge["bridge_meta_valid"])
        self.assertEqual(bridge["mapped_auto_high"],1)
        self.assertEqual(bridge["review"],0)
        self.assertEqual(bridge["unmapped"],0)
        self.assertFalse(bridge["fuzzy_string_matching_used"])
        self.assertNotIn("PBK14_HISTORICAL_MARKET_BRIDGE_NOT_MATERIALIZED",report["gaps"])
        self.assertNotIn("PBK14_HISTORICAL_MARKET_BRIDGE_INVALID",report["gaps"])
        self.assertNotIn("PBK14_HISTORICAL_MARKET_BRIDGE_PARTIAL_MAPPING",report["gaps"])
        self.assertIn("PBK16_HISTORICAL_MARKET_SOURCE_LIMITED_TO_14_LEAGUES",report["gaps"])

    def test_review_rows_remain_fail_closed_and_visible(self):
        self.materialize("REVIEW")
        report=readiness.build_report(self.ops,archive_dir="")
        bridge=report["pbk14_historical_market_bridge"]
        self.assertEqual(bridge["mapped_auto_high"],0)
        self.assertEqual(bridge["review"],1)
        self.assertIn("PBK14_HISTORICAL_MARKET_BRIDGE_PARTIAL_MAPPING",report["gaps"])
        self.assertNotIn("PBK14_HISTORICAL_MARKET_BRIDGE_INVALID",report["gaps"])

    def test_missing_materialization_is_explicit(self):
        report=readiness.build_report(self.ops,archive_dir="")
        self.assertIn("PBK14_HISTORICAL_MARKET_BRIDGE_NOT_MATERIALIZED",report["gaps"])


if __name__=="__main__":
    unittest.main()
