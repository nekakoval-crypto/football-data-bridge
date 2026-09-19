import unittest

from scripts import standings_format_registry as registry


class HistoricalTop5MotivationFormatRegistryTests(unittest.TestCase):
    def test_all_45_top5_season_cells_are_materialized(self):
        self.assertEqual(len(registry.HISTORICAL_TOP5_SEASONS),9)
        expected={(league,season) for league in ("E0","SP1","I1","D1","F1") for season in registry.HISTORICAL_TOP5_SEASONS}
        self.assertEqual(set(registry.HISTORICAL_TOP5_FORMATS),expected)
        self.assertEqual(len(expected),45)

    def test_england_spain_italy_have_20_clubs_38_matches(self):
        for league in ("E0","SP1","I1"):
            for season in registry.HISTORICAL_TOP5_SEASONS:
                item=registry.get_historical_top5_format(league,season)
                self.assertEqual(item["status"],"VERIFIED_RULE_CONTRACT")
                self.assertEqual(item["team_count"],20)
                self.assertEqual(item["total_games"],38)
                self.assertEqual(item["safe_rank"],17)
                self.assertEqual(item["direct_relegation_start_rank"],18)
                self.assertIsNone(item["relegation_playoff_rank"])
                self.assertEqual(item["europe_status"],"UNKNOWN_BY_DESIGN")

    def test_bundesliga_has_playoff_rank_16(self):
        item=registry.get_historical_top5_format("D1","2024/2025")
        self.assertEqual(item["team_count"],18)
        self.assertEqual(item["total_games"],34)
        self.assertEqual(item["safe_rank"],15)
        self.assertEqual(item["relegation_playoff_rank"],16)
        self.assertEqual(item["direct_relegation_start_rank"],17)

    def test_ligue1_transition_is_explicit(self):
        before=registry.get_historical_top5_format("F1","2021/2022")
        transition=registry.get_historical_top5_format("F1","2022/2023")
        after=registry.get_historical_top5_format("F1","2023/2024")

        self.assertEqual((before["team_count"],before["total_games"]),(20,38))
        self.assertEqual(before["relegation_playoff_rank"],18)
        self.assertEqual(before["direct_relegation_start_rank"],19)

        self.assertEqual((transition["team_count"],transition["total_games"]),(20,38))
        self.assertIsNone(transition["relegation_playoff_rank"])
        self.assertEqual(transition["safe_rank"],16)
        self.assertEqual(transition["direct_relegation_start_rank"],17)

        self.assertEqual((after["team_count"],after["total_games"]),(18,34))
        self.assertEqual(after["relegation_playoff_rank"],16)
        self.assertEqual(after["direct_relegation_start_rank"],17)

    def test_2019_20_france_keeps_preseason_format_contract(self):
        item=registry.get_historical_top5_format("F1","2019/2020")
        self.assertEqual(item["total_games"],38)
        self.assertIn("curtailed",item["reason"])
        self.assertIn("information known before",item["reason"])

    def test_recent_serie_a_marks_conditional_tie_playoff_without_fixed_rank(self):
        old=registry.get_historical_top5_format("I1","2021/2022")
        recent=registry.get_historical_top5_format("I1","2022/2023")
        self.assertFalse(old["conditional_safety_playoff_if_tied"])
        self.assertTrue(recent["conditional_safety_playoff_if_tied"])
        self.assertIsNone(recent["relegation_playoff_rank"])

    def test_unknown_scope_fails_closed(self):
        item=registry.get_historical_top5_format("E0","2016/2017")
        self.assertEqual(item["status"],"UNKNOWN")
        self.assertIsNone(item["total_games"])
        self.assertEqual(item["europe_status"],"UNKNOWN_BY_DESIGN")


if __name__=="__main__":
    unittest.main()
