import unittest
from datetime import date

from scripts import standings_format_registry as registry
from scripts import stage80_top5_historical_motivation as m


def state(played,points,gf=40,ga=30):
    return {"played":played,"points":points,"gf":gf,"ga":ga,"history":[]}


def full_epl_states():
    # Unique point totals except where a test intentionally overrides them.
    points=[80,78,70,65,60,58,55,52,49,47,45,43,41,39,37,35,30,27,24,20]
    return {
        f"T{i+1}":state(37,p,gf=60-i,ga=25+i)
        for i,p in enumerate(points)
    }


class HistoricalMotivationProjectionTests(unittest.TestCase):
    def test_run_in_title_draw_path_is_explicit_not_generic_must_win(self):
        states=full_epl_states()
        table=m.ranked_table(states)
        fmt=registry.get_historical_top5_format("E0","2024/2025")
        ctx=m.team_context("T2",table,fmt)
        self.assertEqual(ctx["phase"],"RUN_IN")
        self.assertEqual(ctx["title_gap"],2)
        self.assertEqual(ctx["title_status"],"ALIVE_BY_MAX_POINTS")
        self.assertTrue(ctx["draw_title_path"])
        self.assertEqual(ctx["primary"],"TITLE")
        self.assertEqual(ctx["pressure"],"HIGH")

    def test_direct_relegation_draw_path_to_current_safe_points(self):
        states=full_epl_states()
        table=m.ranked_table(states)
        fmt=registry.get_historical_top5_format("E0","2024/2025")
        ctx=m.team_context("T18",table,fmt)
        self.assertEqual(ctx["position_status"],"IN_DIRECT_RELEGATION_ZONE")
        self.assertEqual(ctx["points_to_safe"],3)
        self.assertTrue(ctx["draw_safe_path"])
        self.assertEqual(ctx["primary"],"SURVIVAL")
        self.assertEqual(ctx["pressure"],"HIGH")

    def test_boundary_points_tie_is_not_presented_as_exact_zone_fact(self):
        states=full_epl_states()
        states["T17"]["points"]=30
        states["T18"]["points"]=30
        # Force GD to keep T17 above T18 while points are tied.
        states["T17"]["gf"],states["T17"]["ga"]=40,30
        states["T18"]["gf"],states["T18"]["ga"]=35,30
        table=m.ranked_table(states)
        fmt=registry.get_historical_top5_format("E0","2024/2025")
        self.assertEqual(m.row_by_rank(table,17)["points"],30)
        self.assertEqual(m.row_by_rank(table,18)["points"],30)
        ctx=m.team_context("T18",table,fmt)
        self.assertEqual(ctx["position_status"],"BOUNDARY_TIE_AMBIGUOUS")

    def test_bundesliga_playoff_position_is_distinct(self):
        states={}
        points=[75,70,64,60,56,53,50,47,44,42,40,38,36,34,32,29,25,20]
        for i,p in enumerate(points):
            states[f"B{i+1}"]=state(33,p,gf=50-i,ga=25+i)
        table=m.ranked_table(states)
        fmt=registry.get_historical_top5_format("D1","2024/2025")
        ctx=m.team_context("B16",table,fmt)
        self.assertEqual(ctx["position_status"],"IN_RELEGATION_PLAYOFF_POSITION")
        self.assertEqual(ctx["primary"],"SURVIVAL")

    def test_incomplete_table_fails_closed(self):
        states={"A":state(1,3),"B":state(1,0)}
        table=m.ranked_table(states)
        fmt=registry.get_historical_top5_format("E0","2024/2025")
        ctx=m.team_context("A",table,fmt)
        self.assertEqual(ctx["title_status"],"UNKNOWN")
        self.assertEqual(ctx["position_status"],"UNKNOWN")
        self.assertEqual(ctx["pressure"],"UNKNOWN")

    def test_same_day_results_are_not_visible_to_each_other(self):
        rows=[
            {
                "historical_match_id":"m1","league_code":"E0","season_label":"2024/2025",
                "date_iso":"2024-08-10","home_team":"A","away_team":"B",
                "ft_result":"H","ft_home_goals":"1","ft_away_goals":"0",
            },
            {
                "historical_match_id":"m2","league_code":"E0","season_label":"2024/2025",
                "date_iso":"2024-08-10","home_team":"C","away_team":"D",
                "ft_result":"D","ft_home_goals":"1","ft_away_goals":"1",
            },
            {
                "historical_match_id":"m3","league_code":"E0","season_label":"2024/2025",
                "date_iso":"2024-08-11","home_team":"A","away_team":"C",
                "ft_result":"A","ft_home_goals":"0","ft_away_goals":"1",
            },
        ]
        out,diag=m.project(rows)
        by_id={r["historical_match_id"]:r for r in out}
        self.assertEqual(diag["invalid_result_rows"],0)
        self.assertEqual(by_id["m1"]["table_teams_with_history"],0)
        self.assertEqual(by_id["m2"]["table_teams_with_history"],0)
        self.assertEqual(by_id["m3"]["table_teams_with_history"],4)
        self.assertEqual(by_id["m3"]["home_points_pre"],3)
        self.assertEqual(by_id["m3"]["away_points_pre"],1)
        self.assertEqual(by_id["m3"]["same_day_results_excluded"],"true")
        self.assertEqual(by_id["m3"]["no_lookahead"],"true")

    def test_europe_is_unknown_by_design_and_unmotivated_is_never_emitted(self):
        states=full_epl_states()
        row={
            "historical_match_id":"x","league_code":"E0","season_label":"2024/2025",
            "date_iso":"2025-05-20","home_team":"T8","away_team":"T9",
        }
        projected=m.feature_row(row,states)
        self.assertEqual(projected["europe_status"],"UNKNOWN_BY_DESIGN")
        self.assertNotIn("unmotivated",str(projected).lower())

    def test_title_elimination_uses_only_current_points_and_max_remaining(self):
        states=full_epl_states()
        states["T3"]["points"]=70
        table=m.ranked_table(states)
        fmt=registry.get_historical_top5_format("E0","2024/2025")
        ctx=m.team_context("T3",table,fmt)
        self.assertEqual(ctx["remaining"],1)
        self.assertEqual(ctx["title_status"],"ELIMINATED_BY_MAX_POINTS")


if __name__=="__main__":
    unittest.main()
