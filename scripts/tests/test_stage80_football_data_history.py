import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_football_data_history import (
    normalize_directory,
    parse_date,
    referee_coverage,
    read_source_text,
    source_specs,
)


class Stage80FootballDataHistoryTests(unittest.TestCase):
    def test_parse_date_variants(self):
        self.assertEqual(parse_date("18/09/2025"), "2025-09-18")
        self.assertEqual(parse_date("18/09/25"), "2025-09-18")
        self.assertEqual(parse_date("bad"), "")

    def test_normalizes_common_results_stats_and_odds(self):
        spec={
            "season_code":"2526","season_label":"2025/2026",
            "league_code":"E0","country":"England","league_name":"Premier League",
            "filename":"2526_E0.csv","url":"https://example/E0.csv",
        }
        text=(
            "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HTR,"
            "Referee,HS,AS,HST,AST,HF,AF,HC,AC,HY,AY,HR,AR,B365H,B365D,B365A,"
            "AvgH,AvgD,AvgA,B365>2.5,B365<2.5,Avg>2.5,Avg<2.5,AHh,B365AHH,B365AHA,"
            "B365CH,B365CD,B365CA,AvgCH,AvgCD,AvgCA,B365C>2.5,B365C<2.5,AvgC>2.5,AvgC<2.5,AHCh,B365CAHH,B365CAHA,AvgCAHH,AvgCAHA\n"
            "E0,18/09/2025,20:00,Alpha,Beta,2,1,H,1,0,H,J. Ref,12,8,5,3,9,11,6,4,2,3,0,0,"
            "1.80,3.60,4.50,1.79,3.58,4.42,1.95,1.85,1.93,1.87,-0.5,1.90,2.00,"
            "1.75,3.70,4.80,1.76,3.66,4.72,1.88,1.92,1.89,1.91,-0.75,1.95,1.95,1.94,1.96\n"
        )
        rows,invalid,columns=read_source_text(text,spec)
        self.assertEqual(invalid,0)
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row["date_iso"],"2025-09-18")
        self.assertEqual(row["home_team"],"Alpha")
        self.assertEqual(row["ft_home_goals"],"2")
        self.assertEqual(row["home_corners"],"6")
        self.assertEqual(row["b365_home"],"1.80")
        self.assertEqual(row["asian_handicap_line"],"-0.5")
        self.assertEqual(row["referee"],"J. Ref")
        self.assertEqual(row["b365_close_home"],"1.75")
        self.assertEqual(row["avg_close_away"],"4.72")
        self.assertEqual(row["b365_close_over_25"],"1.88")
        self.assertEqual(row["asian_handicap_close_line"],"-0.75")
        self.assertEqual(row["avg_close_ah_away"],"1.96")
        self.assertEqual(row["historical_backfill_only"],"true")
        self.assertEqual(row["probability_mutation"],"false")
        self.assertIn("B365H",columns)

    def test_missing_metric_is_unknown_not_zero(self):
        spec={
            "season_code":"1718","season_label":"2017/2018",
            "league_code":"F1","country":"France","league_name":"Ligue 1",
            "filename":"1718_F1.csv","url":"https://example/F1.csv",
        }
        text="Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nF1,01/08/2017,A,B,1,1,D\n"
        rows,invalid,_=read_source_text(text,spec)
        self.assertEqual(invalid,0)
        self.assertEqual(rows[0]["home_shots"],"")
        self.assertEqual(rows[0]["b365_home"],"")

    def test_directory_reports_missing_sources_without_faking_rows(self):
        config={
            "source_base":"https://example",
            "seasons":[{"code":"2526","label":"2025/2026"}],
            "leagues":[
                {"code":"E0","country":"England","league_name":"Premier League"},
                {"code":"D1","country":"Germany","league_name":"Bundesliga"},
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"2526_E0.csv").write_text(
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nE0,18/09/2025,A,B,1,0,H\n",
                encoding="utf-8",
            )
            rows,sources,invalid=normalize_directory(config,root)
        self.assertEqual(len(rows),1)
        self.assertEqual(invalid,0)
        self.assertEqual(sum(1 for x in sources if x["present"]),1)
        self.assertEqual(sum(1 for x in sources if not x["present"]),1)

    def test_referee_coverage_is_explicit_and_league_scoped(self):
        rows=[
            {"league_code":"E0","referee":"A. Ref"},
            {"league_code":"E0","referee":"B. Ref"},
            {"league_code":"F1","referee":""},
        ]
        coverage=referee_coverage(rows)
        self.assertEqual(coverage["referee_rows"],2)
        self.assertEqual(coverage["referee_coverage_pct"],66.67)
        self.assertEqual(coverage["referee_rows_by_league"],{"E0":2})

    def test_config_scope_is_45_files(self):
        config=json.loads(Path("config/stage80_football_data_top5_9seasons.json").read_text(encoding="utf-8"))
        specs=list(source_specs(config))
        self.assertEqual(len(specs),45)
        self.assertEqual(len({x["season_code"] for x in specs}),9)
        self.assertEqual(len({x["league_code"] for x in specs}),5)


if __name__=="__main__":
    unittest.main()
