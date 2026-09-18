import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_archive_manifest import build_manifest
from scripts.stage80_archive_readiness import build_report


class Stage80Top5RefereeBackfillReadinessTests(unittest.TestCase):
    def write_csv(self,path,fieldnames,rows):
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fieldnames)
            w.writeheader(); w.writerows(rows)

    def test_complete_top5_backfill_removes_epl_only_gap(self):
        with tempfile.TemporaryDirectory() as td:
            ops=Path(td)
            self.write_csv(
                ops/"top5_referee_fixture_history.csv",
                [
                    "fixture_id","provider_league_id","season","kickoff_utc","captured_at_utc",
                    "home_team_id","away_team_id","referee","historical_backfill_only",
                    "research_only","operational_betting_authority",
                ],
                [{
                    "fixture_id":"1","provider_league_id":"39","season":"2025",
                    "kickoff_utc":"2025-08-01T15:00:00Z","captured_at_utc":"2026-09-18T20:00:00Z",
                    "home_team_id":"10","away_team_id":"20","referee":"A Ref",
                    "historical_backfill_only":"true","research_only":"true",
                    "operational_betting_authority":"false",
                }],
            )
            self.write_csv(
                ops/"top5_referee_profiles_research.csv",
                [
                    "provider_league_id","referee","first_date","last_date","source_scope",
                    "research_only","operational_betting_authority",
                ],
                [{
                    "provider_league_id":"39","referee":"A Ref","first_date":"2025-08-01",
                    "last_date":"2025-08-01","source_scope":"TOP5_9_SEASONS_API_FOOTBALL",
                    "research_only":"true","operational_betting_authority":"false",
                }],
            )
            self.write_csv(
                ops/"top5_referee_team_splits_research.csv",
                [
                    "provider_league_id","referee","team_id","first_date","last_date",
                    "source_scope","research_only","operational_betting_authority",
                ],
                [{
                    "provider_league_id":"39","referee":"A Ref","team_id":"10",
                    "first_date":"2025-08-01","last_date":"2025-08-01",
                    "source_scope":"TOP5_9_SEASONS_API_FOOTBALL",
                    "research_only":"true","operational_betting_authority":"false",
                }],
            )
            state=[]
            for lid in (39,61,78,135,140):
                for season in range(2017,2026):
                    state.append({
                        "provider_league_id":str(lid),"season":str(season),
                        "last_attempt_at_utc":"2026-09-18T20:00:00Z","status":"CAPTURED",
                    })
            self.write_csv(
                ops/"stage80_top5_referee_backfill_state.csv",
                ["provider_league_id","season","last_attempt_at_utc","status"],
                state,
            )
            (ops/"stage80_top5_referee_backfill_last_run.json").write_text(
                json.dumps({
                    "status":"OK","expected_queries":45,"captured_queries":45,
                    "pending_or_error_queries":0,"archive_rows":1,"profile_rows":1,
                    "team_split_rows":1,"research_only":True,
                    "operational_betting_authority":False,
                }),
                encoding="utf-8",
            )

            report=build_report(ops=ops)
            top5=report["referee_top5_backfill"]
            self.assertTrue(top5["meta_valid"])
            self.assertEqual(top5["captured_league_seasons"],45)
            self.assertEqual(top5["valid_fixture_rows"],1)
            self.assertEqual(top5["referee_coverage_pct"],100.0)
            self.assertNotIn("REFEREE_HISTORY_TOP5_PARTIAL_EPL_ONLY",report["gaps"])
            self.assertNotIn("REFEREE_HISTORY_TOP5_BACKFILL_INVALID_OR_INCOMPLETE",report["gaps"])
            self.assertNotIn("REFEREE_HISTORY_TOP5_PROVIDER_REFEREE_FIELD_PARTIAL",report["gaps"])

            manifest=build_manifest(ops=ops)
            fixture=next(x for x in manifest["datasets"] if x["dataset_id"]=="top5_referee_fixture_history")
            profiles=next(x for x in manifest["datasets"] if x["dataset_id"]=="top5_referee_profiles_research")
            splits=next(x for x in manifest["datasets"] if x["dataset_id"]=="top5_referee_team_splits_research")
            state_entry=next(x for x in manifest["datasets"] if x["dataset_id"]=="stage80_top5_referee_backfill_state")
            self.assertEqual(fixture["contract_status"],"OK")
            self.assertEqual(profiles["contract_status"],"OK")
            self.assertEqual(splits["contract_status"],"OK")
            self.assertEqual(state_entry["contract_status"],"OK")


if __name__=="__main__":
    unittest.main()
