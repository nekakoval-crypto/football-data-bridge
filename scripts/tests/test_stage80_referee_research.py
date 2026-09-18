import unittest

from scripts.stage80_referee_research import aggregate_referees, aggregate_team_splits


class RefereeResearchTests(unittest.TestCase):
    def rows(self):
        return [
            {
                "league_code":"E0","season_label":"2025/26","date_iso":"2025-08-01","referee":"A Ref",
                "home_team":"Alpha","away_team":"Beta","ft_result":"H","ft_home_goals":"2","ft_away_goals":"1",
                "home_yellows":"1","away_yellows":"3","home_reds":"0","away_reds":"1","home_fouls":"10","away_fouls":"14",
            },
            {
                "league_code":"E0","season_label":"2025/26","date_iso":"2025-08-08","referee":"A Ref",
                "home_team":"Gamma","away_team":"Alpha","ft_result":"D","ft_home_goals":"0","ft_away_goals":"0",
                "home_yellows":"2","away_yellows":"2","home_reds":"0","away_reds":"0","home_fouls":"12","away_fouls":"11",
            },
            {
                "league_code":"E0","season_label":"2024/25","date_iso":"2025-01-01","referee":"B Ref",
                "home_team":"Beta","away_team":"Gamma","ft_result":"A","ft_home_goals":"1","ft_away_goals":"3",
                "home_yellows":"","away_yellows":"","home_reds":"0","away_reds":"0","home_fouls":"9","away_fouls":"8",
            },
        ]

    def test_referee_profile_counts_results_and_cards(self):
        profiles={x["referee"]:x for x in aggregate_referees(self.rows())}
        a=profiles["A Ref"]
        self.assertEqual(a["matches"],2)
        self.assertEqual(a["home_wins"],1)
        self.assertEqual(a["draws"],1)
        self.assertEqual(a["away_wins"],0)
        self.assertEqual(a["yellow_observed_matches"],2)
        self.assertEqual(a["home_yellows"],3)
        self.assertEqual(a["away_yellows"],5)
        self.assertEqual(a["total_yellows"],8)
        self.assertEqual(a["total_yellows_per_observed_match"],4.0)
        self.assertEqual(a["home_minus_away_yellows_per_observed_match"],-1.0)
        self.assertEqual(a["source_scope"],"EPL_ONLY")
        self.assertEqual(a["penalties_available"],"false")

    def test_missing_metric_is_not_zero_filled(self):
        profiles={x["referee"]:x for x in aggregate_referees(self.rows())}
        b=profiles["B Ref"]
        self.assertEqual(b["matches"],1)
        self.assertEqual(b["yellow_observed_matches"],0)
        self.assertIsNone(b["total_yellows_per_observed_match"])

    def test_team_split_uses_team_perspective(self):
        splits={(x["referee"],x["team"]):x for x in aggregate_team_splits(self.rows())}
        alpha=splits[("A Ref","Alpha")]
        self.assertEqual(alpha["matches"],2)
        self.assertEqual(alpha["home_matches"],1)
        self.assertEqual(alpha["away_matches"],1)
        self.assertEqual(alpha["wins"],1)
        self.assertEqual(alpha["draws"],1)
        self.assertEqual(alpha["losses"],0)
        self.assertEqual(alpha["points"],4)
        self.assertEqual(alpha["goals_for"],2)
        self.assertEqual(alpha["goals_against"],1)
        self.assertEqual(alpha["yellows_for"],3)
        self.assertEqual(alpha["yellows_against"],5)


if __name__=="__main__":
    unittest.main()
