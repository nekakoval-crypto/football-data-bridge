import json
import unittest
import scripts.player_synergy_validation as p

class PlayerSynergyValidationTests(unittest.TestCase):
    def test_no_vig_probability_normalizes_market(self):
        x=p.no_vig_win(2.0,4.0,4.0)
        self.assertAlmostEqual(x,0.5)

    def test_market_join_is_exact_fixture_only(self):
        wf=[{"fixture_id":"10","kickoff_utc":"2026-01-01T12:00:00+00:00","team_id":"1","team_name":"A","side":"HOME",
             "pair_eligible_prior":"2","pair_points_delta_mean":"0.1","trio_eligible_prior":"0","trio_points_delta_mean":"",
             "line_eligible_prior":"0","line_points_delta_mean":""}]
        market=[{"api_fixture_id":"10","historical_match_id":"m","mapping_status":"AUTO","fuzzy_string_matching_used":"false",
                 "one_to_one_verified":"true","avg_close_home":"2.0","avg_close_draw":"4.0","avg_close_away":"4.0","ft_result":"H"}]
        rows=p.build_market_validation(wf,market)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["actual_win"],1)
        self.assertAlmostEqual(rows[0]["market_no_vig_win_probability"],0.5)

    def test_latest_official_lineup_rejects_postkickoff_capture(self):
        xi=json.dumps([{"id":str(i),"name":str(i)} for i in range(11)])
        rows=[{"fixture_id":"1","team_id":"T","official_lineup":"YES",
               "captured_at_utc":"2026-01-01T12:01:00Z","kickoff_utc":"2026-01-01T12:00:00Z",
               "starting_xi_json":xi}]
        self.assertEqual(p.latest_official_lineups(rows),{})

    def test_substitution_uses_player_out_and_assist_in(self):
        xi=json.dumps([{"id":str(i),"name":str(i)} for i in range(1,12)])
        lineups=[{"fixture_id":"1","team_id":"T","team_name":"A","side":"HOME","official_lineup":"YES",
                  "captured_at_utc":"2026-01-01T11:50:00Z","kickoff_utc":"2026-01-01T12:00:00Z","starting_xi_json":xi}]
        events=[{"fixture_id":"1","team_id":"T","team_name":"A","event_type":"subst","elapsed":"60",
                 "player_id":"1","player_name":"OUT","assist_id":"99","assist_name":"IN","observed_at_utc":"2026-01-01T14:00:00Z"}]
        rows=p.build_substitutions(lineups,events)
        self.assertEqual(rows[0]["out_was_starter"],"YES")
        self.assertEqual(rows[0]["in_was_starter"],"NO")
        self.assertEqual(rows[0]["transition_key"],"T:1->99")

    def test_pearson_requires_variance(self):
        self.assertIsNone(p.pearson([1,1,1],[0,1,0]))

if __name__=="__main__":
    unittest.main()
