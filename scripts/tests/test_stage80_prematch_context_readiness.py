import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_archive_manifest import build_manifest
from scripts.stage80_archive_readiness import build_report


class Stage80PrematchContextReadinessTests(unittest.TestCase):
    FIELDS = [
        "historical_match_id","league_code","season_label","date_iso","time_local",
        "home_team","away_team","same_day_results_excluded","no_lookahead",
        "historical_backfill_only","research_only","operational_betting_authority",
        "creates_signal","probability_mutation","eligibility_mutation","stake_changes",
        "forward_journal_mutation",
    ]

    def write_complete_archive(self, ops: Path):
        leagues=["D1","E0","F1","I1","SP1"]
        seasons=[f"{year}/{year+1}" for year in range(2017,2026)]
        pairs=[(league,season) for league in leagues for season in seasons]
        target=ops/"top5_prematch_context_research.csv"
        with target.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=self.FIELDS)
            w.writeheader()
            for i in range(16111):
                league,season=pairs[i % len(pairs)]
                w.writerow({
                    "historical_match_id":f"m{i+1}",
                    "league_code":league,
                    "season_label":season,
                    "date_iso":"2025-01-01",
                    "time_local":"15:00",
                    "home_team":"Home",
                    "away_team":"Away",
                    "same_day_results_excluded":"true",
                    "no_lookahead":"true",
                    "historical_backfill_only":"true",
                    "research_only":"true",
                    "operational_betting_authority":"false",
                    "creates_signal":"false",
                    "probability_mutation":"false",
                    "eligibility_mutation":"false",
                    "stake_changes":"false",
                    "forward_journal_mutation":"false",
                })
        meta={
            "version":"PBK_STAGE80_FOOTBALL_DATA_PREMATCH_CONTEXT_V1",
            "status":"OK",
            "source_rows":16111,
            "output_rows":16111,
            "unique_historical_match_ids":16111,
            "league_codes":leagues,
            "season_labels":seasons,
            "invalid_date_rows":0,
            "duplicate_historical_match_ids":0,
            "invalid_result_rows":0,
            "rows_with_kickoff_time":12459,
            "rows_with_both_rest":15660,
            "rows_with_both_pre_match_rank":15660,
            "rows_with_both_full_last5":13903,
            "rows_with_both_full_last10":11704,
            "same_day_results_excluded":True,
            "no_lookahead":True,
            "provider_calls":0,
            "historical_backfill_only":True,
            "research_only":True,
            "operational_betting_authority":False,
            "creates_signal":False,
            "probability_mutation":False,
            "eligibility_mutation":False,
            "stake_changes":False,
            "forward_journal_mutation":False,
        }
        (ops/"stage80_prematch_context_last_run.json").write_text(
            json.dumps(meta),encoding="utf-8"
        )

    def test_missing_archive_is_explicit_gap(self):
        with tempfile.TemporaryDirectory() as td:
            report=build_report(Path(td))
            self.assertIn("PREMATCH_CONTEXT_TOP5_NOT_MATERIALIZED",report["gaps"])

    def test_complete_archive_is_valid_and_registered(self):
        with tempfile.TemporaryDirectory() as td:
            ops=Path(td)
            self.write_complete_archive(ops)
            report=build_report(ops)
            self.assertNotIn("PREMATCH_CONTEXT_TOP5_NOT_MATERIALIZED",report["gaps"])
            self.assertNotIn("PREMATCH_CONTEXT_TOP5_INVALID_OR_INCOMPLETE",report["gaps"])
            block=report["prematch_context_research"]
            self.assertEqual(block["valid_rows"],16111)
            self.assertEqual(block["unique_historical_match_ids"],16111)
            self.assertEqual(block["league_seasons"],45)
            self.assertTrue(block["no_lookahead"])
            self.assertFalse(block["operational_betting_authority"])

            manifest=build_manifest(ops)
            entry=next(
                item for item in manifest["datasets"]
                if item["dataset_id"]=="top5_prematch_context_research"
            )
            self.assertTrue(entry["present"])
            self.assertEqual(entry["row_count"],16111)
            self.assertEqual(entry["contract_status"],"OK")


if __name__=="__main__":
    unittest.main()
