import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import stage80_top5_referee_backfill as s


def payload(fid, league, season, referee="A Ref", home=1, away=0):
    return {
        "errors": [],
        "paging": {"current": 1, "total": 1},
        "response": [{
            "fixture": {
                "id": fid,
                "referee": referee,
                "date": f"{season}-08-12T15:00:00+00:00",
                "status": {"short": "FT"},
                "venue": {"id": 10, "name": "Ground", "city": "City"},
            },
            "league": {
                "id": league, "name": "League", "country": "Country",
                "season": season, "round": "Regular Season - 1",
            },
            "teams": {
                "home": {"id": 100+fid, "name": "Home"},
                "away": {"id": 200+fid, "name": "Away"},
            },
            "goals": {"home": home, "away": away},
        }],
    }


class Top5RefereeBackfillTests(unittest.TestCase):
    def test_real_config_is_exact_45_cell_matrix(self):
        cfg,matrix=s.load_config()
        self.assertEqual(cfg["expected_queries"],45)
        self.assertEqual(len(matrix),45)
        self.assertEqual({x["provider_league_id"] for x in matrix},{39,61,78,135,140})
        self.assertEqual({x["season"] for x in matrix},set(range(2017,2026)))

    def test_normalize_preserves_referee_and_result(self):
        rows=s.normalize_payload(
            payload(1,39,2025,referee="A Ref",home=2,away=1),
            {"provider_league_id":39,"league_name":"Premier League","country":"England","season":2025},
            "2026-09-18T20:00:00Z",
        )
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["referee"],"A Ref")
        self.assertEqual(rows[0]["result"],"H")
        self.assertEqual(rows[0]["research_only"],"true")
        self.assertEqual(rows[0]["operational_betting_authority"],"false")

    def test_profiles_are_league_scoped(self):
        base={
            "season":"2025","kickoff_utc":"2025-08-12T15:00:00Z",
            "home_team_id":"1","home_team":"A","away_team_id":"2","away_team":"B",
            "home_goals":"1","away_goals":"0","result":"H","referee":"Same Ref",
        }
        rows=[
            {**base,"provider_league_id":"39","league_name":"Premier League","country":"England","fixture_id":"1"},
            {**base,"provider_league_id":"140","league_name":"La Liga","country":"Spain","fixture_id":"2"},
        ]
        profiles=s.aggregate_profiles(rows)
        self.assertEqual(len(profiles),2)
        self.assertEqual({x["provider_league_id"] for x in profiles},{"39","140"})

    def test_run_resumes_captured_cells_without_recalling_provider(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            config=root/"config.json"
            config.write_text(json.dumps({
                "version":"TEST","seasons":[2024,2025],
                "leagues":[{"provider_league_id":39,"league_name":"Premier League","country":"England"}],
                "expected_queries":2,
            }),encoding="utf-8")

            calls=[]
            def fake_get(path,params=None,**kwargs):
                calls.append((path,dict(params or {})))
                season=int(params["season"])
                return payload(season,39,season,referee="Ref "+str(season))

            globals_patch={
                "OPS":root,
                "ARCHIVE":root/"archive.csv",
                "PROFILES":root/"profiles.csv",
                "TEAM_SPLITS":root/"splits.csv",
                "QUERY_STATE":root/"state.csv",
                "META":root/"meta.json",
                "SHARED_STATE":root/"shared.json",
            }
            with patch.multiple(s,**globals_patch):
                meta1=s.run(config,get=fake_get,now=datetime(2026,9,18,20,0,tzinfo=timezone.utc))
                self.assertEqual(meta1["captured_queries"],2)
                self.assertEqual(len(calls),2)
                self.assertEqual(meta1["archive_rows"],2)

                meta2=s.run(config,get=fake_get,now=datetime(2026,9,18,20,5,tzinfo=timezone.utc))
                self.assertEqual(meta2["captured_queries"],2)
                self.assertEqual(len(calls),2)
                self.assertEqual(meta2["provider_budget_calls"],0)

                with (root/"profiles.csv").open(encoding="utf-8-sig",newline="") as f:
                    profiles=list(csv.DictReader(f))
                self.assertEqual(sum(int(r["matches"]) for r in profiles),2)


if __name__=="__main__":
    unittest.main()
