import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_archive_manifest import build_manifest
from scripts.stage80_archive_readiness import build_report


class Stage80RefereeResearchReadinessTests(unittest.TestCase):
    def write_csv(self,path,fieldnames,rows):
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    def test_durable_referee_research_is_reported_and_manifested(self):
        with tempfile.TemporaryDirectory() as td:
            ops=Path(td)
            self.write_csv(
                ops/"epl_referee_profiles_research.csv",
                ["referee","first_date","last_date","source_scope","research_only","operational_betting_authority"],
                [{
                    "referee":"A Ref","first_date":"2025-01-01","last_date":"2025-08-01",
                    "source_scope":"EPL_ONLY","research_only":"true","operational_betting_authority":"false",
                }],
            )
            self.write_csv(
                ops/"epl_referee_team_splits_research.csv",
                ["referee","team","first_date","last_date","source_scope","research_only","operational_betting_authority"],
                [{
                    "referee":"A Ref","team":"Alpha","first_date":"2025-01-01","last_date":"2025-08-01",
                    "source_scope":"EPL_ONLY","research_only":"true","operational_betting_authority":"false",
                }],
            )
            (ops/"stage80_referee_research_last_run.json").write_text(
                json.dumps({
                    "status":"OK","source_scope":"EPL_ONLY","source_rows":3420,
                    "unique_referees":1,"referee_team_pairs":1,
                    "research_only":True,"operational_betting_authority":False,"provider_calls":0,
                }),
                encoding="utf-8",
            )

            report=build_report(ops=ops)
            referee=report["referee_research"]
            self.assertTrue(referee["meta_valid"])
            self.assertEqual(referee["unique_referees"],1)
            self.assertEqual(referee["valid_team_split_rows"],1)
            self.assertEqual(referee["source_matches"],3420)
            self.assertFalse(referee["penalties_available"])
            self.assertFalse(referee["operational_betting_authority"])
            self.assertNotIn("REFEREE_RESEARCH_NOT_MATERIALIZED",report["gaps"])
            self.assertNotIn("REFEREE_RESEARCH_INVALID",report["gaps"])
            self.assertIn("REFEREE_HISTORY_TOP5_PARTIAL_EPL_ONLY",report["gaps"])

            manifest=build_manifest(ops=ops)
            profiles=next(x for x in manifest["datasets"] if x["dataset_id"]=="epl_referee_profiles_research")
            splits=next(x for x in manifest["datasets"] if x["dataset_id"]=="epl_referee_team_splits_research")
            self.assertTrue(profiles["present"])
            self.assertEqual(profiles["row_count"],1)
            self.assertEqual(profiles["contract_status"],"OK")
            self.assertTrue(splits["present"])
            self.assertEqual(splits["row_count"],1)
            self.assertEqual(splits["contract_status"],"OK")


if __name__=="__main__":
    unittest.main()
