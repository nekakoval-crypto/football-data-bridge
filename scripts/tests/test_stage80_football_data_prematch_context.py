import unittest

from scripts.stage80_football_data_prematch_context import project


def row(mid,day,home,away,result,hg,ag,time="15:00",league="E0",season="2025/26"):
    return {
        "historical_match_id":mid,
        "league_code":league,
        "league_name":"League",
        "country":"Country",
        "season_label":season,
        "date_iso":day,
        "time_local":time,
        "home_team":home,
        "away_team":away,
        "ft_result":result,
        "ft_home_goals":str(hg),
        "ft_away_goals":str(ag),
    }


class FootballDataPrematchContextTests(unittest.TestCase):
    def keyed(self,rows):
        out,diag=project(rows)
        return {r["historical_match_id"]:r for r in out},diag

    def test_same_day_results_never_leak_between_matches(self):
        rows=[
            row("m1","2025-08-01","A","B","H",2,0),
            row("m2","2025-08-08","A","C","H",1,0,"12:00"),
            row("m3","2025-08-08","C","D","H",3,0,"20:00"),
        ]
        k,diag=self.keyed(rows)
        self.assertEqual(diag["invalid_result_rows"],0)
        self.assertEqual(k["m2"]["home_played_pre"],1)
        self.assertEqual(k["m2"]["away_played_pre"],0)
        self.assertEqual(k["m3"]["home_played_pre"],0)
        self.assertEqual(k["m3"]["home_points_pre"],0)
        self.assertEqual(k["m3"]["home_form_matches_last5"],0)
        self.assertEqual(k["m3"]["same_day_results_excluded"],"true")
        self.assertEqual(k["m3"]["no_lookahead"],"true")

    def test_rest_form_and_table_state_use_only_prior_dates(self):
        rows=[
            row("m1","2025-08-01","A","B","H",2,0),
            row("m2","2025-08-05","C","A","D",1,1),
            row("m3","2025-08-10","A","C","A",0,1),
        ]
        k,_=self.keyed(rows)
        m3=k["m3"]
        self.assertEqual(m3["home_played_pre"],2)
        self.assertEqual(m3["home_points_pre"],4)
        self.assertEqual(m3["home_gf_pre"],3)
        self.assertEqual(m3["home_ga_pre"],1)
        self.assertEqual(m3["home_rest_days"],5)
        self.assertEqual(m3["away_rest_days"],5)
        self.assertEqual(m3["rest_advantage_days"],0)
        self.assertEqual(m3["home_form_matches_last5"],2)
        self.assertEqual(m3["home_points_last5"],4)
        self.assertEqual(m3["home_ppg_last5"],2.0)
        self.assertEqual(m3["away_form_matches_last5"],1)
        self.assertEqual(m3["away_points_last5"],1)
        self.assertEqual(m3["home_rank_pre"],1)
        self.assertEqual(m3["away_rank_pre"],2)
        self.assertEqual(m3["table_teams_with_history"],3)

    def test_congestion_windows_exclude_current_match(self):
        rows=[
            row("m1","2025-08-01","A","B","H",1,0),
            row("m2","2025-08-04","C","A","D",0,0),
            row("m3","2025-08-07","A","D","H",2,0),
        ]
        k,_=self.keyed(rows)
        m3=k["m3"]
        self.assertEqual(m3["home_rest_days"],3)
        self.assertEqual(m3["home_short_rest_le3d"],"true")
        self.assertEqual(m3["home_matches_prev_7d"],2)
        self.assertEqual(m3["home_matches_prev_14d"],2)
        self.assertEqual(m3["away_matches_prev_7d"],0)

    def test_weekday_and_local_time_are_descriptive_only(self):
        rows=[
            row("mon","2025-09-15","A","B","D",1,1,"17:30"),
            row("thu","2025-09-18","C","D","D",0,0,""),
        ]
        k,_=self.keyed(rows)
        self.assertEqual(k["mon"]["weekday_name"],"MONDAY")
        self.assertEqual(k["mon"]["is_monday"],"true")
        self.assertEqual(k["mon"]["is_thursday"],"false")
        self.assertEqual(k["mon"]["kickoff_minutes_local"],1050)
        self.assertEqual(k["thu"]["weekday_name"],"THURSDAY")
        self.assertEqual(k["thu"]["is_thursday"],"true")
        self.assertEqual(k["thu"]["kickoff_minutes_local"],"")

    def test_league_season_state_isolated(self):
        rows=[
            row("e0","2025-08-01","A","B","H",1,0,league="E0",season="2025/26"),
            row("d1","2025-08-08","A","C","H",1,0,league="D1",season="2025/26"),
            row("e0new","2026-08-01","A","D","H",1,0,league="E0",season="2026/27"),
        ]
        k,_=self.keyed(rows)
        self.assertEqual(k["d1"]["home_played_pre"],0)
        self.assertEqual(k["e0new"]["home_played_pre"],0)


if __name__=="__main__":
    unittest.main()
