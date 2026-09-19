import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_football_data_pbk14_history as h
from scripts import stage80_pbk14_fixture_bridge as b


class PBK14HistoryTests(unittest.TestCase):
    def test_config_is_14_supported_plus_2_explicit_unsupported(self):
        cfg=h.load_config()
        self.assertEqual(len(cfg["leagues"]),14)
        self.assertEqual(len(cfg["unsupported_pbk_leagues"]),2)
        self.assertEqual(
            {x["country"] for x in cfg["unsupported_pbk_leagues"]},
            {"Lithuania","Latvia"},
        )
        self.assertEqual(
            {x["source_code"] for x in cfg["leagues"]},
            {"E0","SP1","I1","D1","F1","SC0","N1","B1","P1","T1","AUT","DNK","NOR","POL"},
        )

    def test_source_matrix_is_90_season_files_plus_4_cumulative_files(self):
        cfg=h.load_config()
        specs=list(h.source_specs(cfg))
        self.assertEqual(len(specs),94)
        self.assertEqual(sum(x["source_mode"]=="SEASON_FILE" for x in specs),90)
        self.assertEqual(sum(x["source_mode"]=="ALL_SEASONS_FILE" for x in specs),4)
        self.assertEqual(
            {x["filename"] for x in specs if x["source_mode"]=="ALL_SEASONS_FILE"},
            {"ALL_AUT.csv","ALL_DNK.csv","ALL_NOR.csv","ALL_POL.csv"},
        )

    def test_extra_row_normalizes_closing_1x2_and_governance(self):
        league={
            "country":"Poland","league_name":"Ekstraklasa",
            "source_code":"POL","extra_source_base":"https://www.football-data.co.uk/new",
        }
        row={
            "Country":"Poland","League":"Ekstraklasa","Season":"2024/2025",
            "Date":"17/08/2024","Time":"18:00","Home":"Lech","Away":"Legia",
            "HG":"2","AG":"1","Res":"H",
            "B365CH":"1.95","B365CD":"3.50","B365CA":"4.10",
            "AvgCH":"1.92","AvgCD":"3.45","AvgCA":"4.05",
        }
        out=h.normalize_extra_row(league,row,2,set(range(2017,2026)))
        self.assertEqual(out["league_code"],"POL")
        self.assertEqual(out["date_iso"],"2024-08-17")
        self.assertEqual(out["ft_result"],"H")
        self.assertEqual(out["avg_close_home"],"1.92")
        self.assertEqual(out["b365_close_away"],"4.10")
        self.assertEqual(out["historical_backfill_only"],"true")
        self.assertEqual(out["creates_signal"],"false")
        self.assertEqual(out["forward_journal_mutation"],"false")

    def test_extra_row_outside_target_window_is_ignored(self):
        league={
            "country":"Poland","league_name":"Ekstraklasa",
            "source_code":"POL","extra_source_base":"https://www.football-data.co.uk/new",
        }
        row={"Season":"2016/2017","Date":"17/08/2016","Home":"A","Away":"B"}
        self.assertIsNone(h.normalize_extra_row(league,row,2,set(range(2017,2026))))


class PBK14BridgeTests(unittest.TestCase):
    def source(self,mid,date,home,away,hg,ag,code="E0",season="2024/2025"):
        return {
            "historical_match_id":mid,"league_code":code,"season_label":season,
            "date_iso":date,"home_team":home,"away_team":away,
            "ft_home_goals":str(hg),"ft_away_goals":str(ag),
        }

    def api(self,fid,date,home_id,home,away_id,away,hg,ag,league_id=39,season=2024):
        return {
            "fixture_id":str(fid),"competition_role":"DOMESTIC_LEAGUE",
            "provider_competition_id":str(league_id),"season":str(season),"status":"FT",
            "kickoff_utc":date+"T15:00:00+00:00",
            "home_team_id":str(home_id),"home_team":home,
            "away_team_id":str(away_id),"away_team":away,
            "home_goals":str(hg),"away_goals":str(ag),
        }

    def test_auto_requires_exact_canonical_team_identity_date_and_score(self):
        src=[self.source("m1","2024-08-10","Bayern München","Borussia Dortmund",2,1,code="D1")]
        api=[self.api(100,"2024-08-10",1,"Bayern Munchen",2,"Borussia Dortmund",2,1,league_id=78)]
        rows=b.map_scope(src,api,"D1",78,2024)
        self.assertEqual(rows[0]["mapping_status"],"AUTO")
        self.assertEqual(rows[0]["api_fixture_id"],"100")
        self.assertEqual(rows[0]["fuzzy_string_matching_used"],"false")
        self.assertEqual(rows[0]["one_to_one_verified"],"true")

    def test_high_uses_unique_schedule_score_fingerprint_not_fuzzy_name(self):
        src=[]
        api=[]
        opponents=["A","B","C","D","E"]
        for i,opp in enumerate(opponents,1):
            day=f"2024-08-{9+i:02d}"
            src.append(self.source(f"m{i}",day,opp,"Mystery Source Club",i%3,(i+1)%3))
            api.append(self.api(200+i,day,100+i,opp,999,"Completely Different Provider Name",i%3,(i+1)%3))
        rows=b.map_scope(src,api,"E0",39,2024)
        self.assertEqual({r["away_team_map_status"] for r in rows},{"HIGH"})
        self.assertEqual({r["mapping_status"] for r in rows},{"HIGH"})
        self.assertTrue(all(r["api_away_team_id"]=="999" for r in rows))
        self.assertEqual({r["away_team_map_method"] for r in rows},{"SCHEDULE_SCORE_FINGERPRINT"})
        self.assertTrue(all(r["fuzzy_string_matching_used"]=="false" for r in rows))

    def test_full_fingerprint_allows_disjoint_source_aliases_for_same_provider_team(self):
        src=[]
        api=[]
        for i in range(1,11):
            day=f"2024-09-{i:02d}"
            alias="Alias One" if i<=5 else "Alias Two"
            opp=f"Opponent {i}"
            src.append(self.source(f"a{i}",day,opp,alias,0,1))
            api.append(self.api(300+i,day,100+i,opp,999,"Provider Club",0,1))
        rows=b.map_scope(src,api,"E0",39,2024)
        self.assertEqual({r["mapping_status"] for r in rows},{"HIGH"})
        self.assertEqual({r["api_away_team_id"] for r in rows},{"999"})
        self.assertEqual(
            {r["away_team_map_method"] for r in rows},
            {"SCHEDULE_SCORE_FINGERPRINT"},
        )
        self.assertEqual(len({r["api_fixture_id"] for r in rows}),10)

    def test_near_complete_fingerprint_is_high_but_discrepant_fixture_stays_review(self):
        src=[]
        api=[]
        for i in range(1,22):
            day=f"2024-10-{i:02d}"
            opp=f"Opponent {i}"
            src.append(self.source(f"n{i}",day,opp,"Source Club",0,1))
            provider_away=2 if i==21 else 1
            api.append(self.api(400+i,day,200+i,opp,888,"Provider Club",0,provider_away))
        rows=b.map_scope(src,api,"E0",39,2024)
        self.assertEqual(sum(r["mapping_status"]=="HIGH" for r in rows),20)
        self.assertEqual(sum(r["mapping_status"]=="REVIEW" for r in rows),1)
        self.assertEqual(
            {r["away_team_map_method"] for r in rows},
            {"NEAR_COMPLETE_SCHEDULE_SCORE_FINGERPRINT"},
        )
        review=next(r for r in rows if r["mapping_status"]=="REVIEW")
        self.assertEqual(review["mapping_reason"],"DATE_TEAMS_MATCH_BUT_SCORE_MISMATCH")
        self.assertTrue(all(r["fuzzy_string_matching_used"]=="false" for r in rows))

    def test_score_mismatch_never_auto_maps(self):
        src=[self.source("m1","2024-08-10","Home","Away",2,1)]
        api=[self.api(1,"2024-08-10",10,"Home",20,"Away",1,1)]
        rows=b.map_scope(src,api,"E0",39,2024)
        self.assertEqual(rows[0]["mapping_status"],"REVIEW")
        self.assertEqual(rows[0]["mapping_reason"],"DATE_TEAMS_MATCH_BUT_SCORE_MISMATCH")

    def test_provider_fixture_reuse_is_demoted_from_auto_high(self):
        src=[
            self.source("m1","2024-08-10","Home","Away",1,0),
            self.source("m2","2024-08-10","Home","Away",1,0),
        ]
        api=[self.api(1,"2024-08-10",10,"Home",20,"Away",1,0)]
        rows=b.map_scope(src,api,"E0",39,2024)
        self.assertEqual({r["mapping_status"] for r in rows},{"REVIEW"})
        self.assertEqual({r["mapping_reason"] for r in rows},{"ONE_TO_ONE_PROVIDER_FIXTURE_CONFLICT"})
        self.assertTrue(all(r["one_to_one_verified"]=="false" for r in rows))


if __name__=="__main__":
    unittest.main()
