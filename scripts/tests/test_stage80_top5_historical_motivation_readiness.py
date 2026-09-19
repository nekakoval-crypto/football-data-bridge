import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_archive_manifest import build_manifest
from scripts.stage80_archive_readiness import build_report


FIELDS=[
    "historical_match_id","league_code","season_label","date_iso","home_team","away_team",
    "format_status","europe_status","rank_tiebreak_contract",
    "full_table_available","boundary_tie_ambiguous",
    "same_day_results_excluded","no_lookahead","historical_backfill_only",
    "research_only","operational_betting_authority","creates_signal",
    "probability_mutation","eligibility_mutation","stake_changes","forward_journal_mutation",
]


class Top5HistoricalMotivationReadinessTests(unittest.TestCase):
    def materialize(self,ops: Path,*,authority=False,europe="UNKNOWN_BY_DESIGN"):
        leagues=["D1","E0","F1","I1","SP1"]
        seasons=[f"{year}/{year+1}" for year in range(2017,2026)]
        pairs=[(league,season) for league in leagues for season in seasons]
        with (ops/"top5_historical_motivation_research.csv").open(
            "w",encoding="utf-8-sig",newline=""
        ) as f:
            w=csv.DictWriter(f,fieldnames=FIELDS)
            w.writeheader()
            for i in range(16111):
                league,season=pairs[i % 45]
                w.writerow({
                    "historical_match_id":f"m{i+1}",
                    "league_code":league,
                    "season_label":season,
                    "date_iso":"2025-01-01",
                    "home_team":"Home","away_team":"Away",
                    "format_status":"VERIFIED_RULE_CONTRACT",
                    "europe_status":europe,
                    "rank_tiebreak_contract":"POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1",
                    "full_table_available":"true" if i < 15631 else "false",
                    "boundary_tie_ambiguous":"true" if i < 4434 else "false",
                    "same_day_results_excluded":"true","no_lookahead":"true",
                    "historical_backfill_only":"true","research_only":"true",
                    "operational_betting_authority":"true" if authority else "false",
                    "creates_signal":"false","probability_mutation":"false",
                    "eligibility_mutation":"false","stake_changes":"false",
                    "forward_journal_mutation":"false",
                })
        meta={
            "version":"PBK_STAGE80_TOP5_HISTORICAL_MOTIVATION_CONTEXT_V1",
            "status":"OK","source_rows":16111,"output_rows":16111,
            "unique_historical_match_ids":16111,
            "league_codes":leagues,"season_labels":seasons,"league_season_cells":45,
            "invalid_date_rows":0,"duplicate_historical_match_ids":0,"invalid_result_rows":0,
            "rows_with_full_table":15631,
            "rows_with_both_title_status":15631,
            "rows_with_both_relegation_status":15631,
            "rows_with_boundary_points_tie":4434,
            "format_contract":"TOP5_45_SEASON_CELLS_V1",
            "rank_tiebreak_contract":"POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1",
            "europe_status":"UNKNOWN_BY_DESIGN",
            "same_day_results_excluded":True,"no_lookahead":True,"provider_calls":0,
            "historical_backfill_only":True,"research_only":True,
            "operational_betting_authority":False,"creates_signal":False,
            "probability_mutation":False,"eligibility_mutation":False,
            "stake_changes":False,"forward_journal_mutation":False,
        }
        (ops/"stage80_top5_historical_motivation_last_run.json").write_text(
            json.dumps(meta),encoding="utf-8"
        )

    def test_complete_layer_closes_readiness_gap_and_manifest_is_ok(self):
        with tempfile.TemporaryDirectory() as td:
            ops=Path(td)
            self.materialize(ops)
            report=build_report(ops,archive_dir="")
            layer=report["top5_historical_motivation_research"]
            self.assertTrue(layer["meta_valid"])
            self.assertEqual(layer["valid_rows"],16111)
            self.assertEqual(layer["league_seasons"],45)
            self.assertEqual(layer["rows_with_full_table"],15631)
            self.assertEqual(layer["rows_with_boundary_points_tie"],4434)
            self.assertEqual(layer["europe_status"],"UNKNOWN_BY_DESIGN")
            self.assertTrue(layer["no_lookahead"])
            self.assertFalse(layer["operational_betting_authority"])
            self.assertNotIn("TOP5_HISTORICAL_MOTIVATION_NOT_MATERIALIZED",report["gaps"])
            self.assertNotIn("TOP5_HISTORICAL_MOTIVATION_INVALID_OR_INCOMPLETE",report["gaps"])

            manifest=build_manifest(ops,raw_archive_dir="")
            item=next(
                x for x in manifest["datasets"]
                if x["dataset_id"]=="top5_historical_motivation_research"
            )
            self.assertEqual(item["contract_status"],"OK")
            self.assertEqual(item["identity_key_text"],"historical_match_id")
            self.assertEqual(item["effective_time_fields_text"],"date_iso")
            self.assertIn("UNKNOWN_BY_DESIGN",item["limitations"])

    def test_authority_or_europe_inference_fails_closed(self):
        for kwargs in ({"authority":True},{"europe":"CHAMPIONS_LEAGUE"}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as td:
                ops=Path(td)
                self.materialize(ops,**kwargs)
                report=build_report(ops,archive_dir="")
                self.assertIn("TOP5_HISTORICAL_MOTIVATION_INVALID_OR_INCOMPLETE",report["gaps"])

    def test_missing_layer_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            report=build_report(Path(td),archive_dir="")
            self.assertIn("TOP5_HISTORICAL_MOTIVATION_NOT_MATERIALIZED",report["gaps"])


if __name__=="__main__":
    unittest.main()
