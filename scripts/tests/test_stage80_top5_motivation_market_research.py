import unittest

from scripts import stage80_top5_motivation_market_research as r


def context(mid="m1"):
    return {
        "historical_match_id":mid,
        "league_code":"E0","season_label":"2024/2025","date_iso":"2025-04-20",
        "home_team":"Home","away_team":"Away",
        "format_status":"VERIFIED_RULE_CONTRACT",
        "europe_status":"UNKNOWN_BY_DESIGN",
        "rank_tiebreak_contract":"POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1",
        "full_table_available":"true",
        "home_season_phase":"RUN_IN","away_season_phase":"RUN_IN",
        "home_pressure":"HIGH","away_pressure":"MEDIUM",
        "pressure_asymmetry":"HOME_HIGHER",
        "home_title_status":"ALIVE_BY_MAX_POINTS",
        "away_title_status":"ALIVE_BY_MAX_POINTS",
        "home_title_gap_points":"2","away_title_gap_points":"7",
        "home_relegation_position_status":"CURRENTLY_SAFE_POSITION",
        "away_relegation_position_status":"IN_DIRECT_RELEGATION_ZONE",
        "home_points_above_danger_boundary":"2",
        "away_points_to_safe_boundary":"1",
        "home_draw_eliminates_title_points_path":"true",
        "away_draw_eliminates_title_points_path":"false",
        "home_draw_insufficient_to_reach_current_safe_points":"false",
        "away_draw_insufficient_to_reach_current_safe_points":"true",
        "same_day_results_excluded":"true","no_lookahead":"true",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
    }


def match(mid="m1"):
    return {
        "historical_match_id":mid,
        "ft_result":"H","ft_home_goals":"2","ft_away_goals":"1",
        "avg_close_home":"2.00","avg_close_draw":"3.50","avg_close_away":"4.00",
        "avg_close_over_25":"1.90","avg_close_under_25":"1.95",
    }


class Top5MotivationMarketResearchTests(unittest.TestCase):
    def test_factor_buckets_are_evidence_bound(self):
        b=r.factor_buckets(context())
        self.assertEqual(b["PRESSURE_ASYMMETRY"],"HOME_HIGHER")
        self.assertEqual(b["HIGH_PRESSURE_SIDE"],"HOME_ONLY")
        self.assertEqual(b["MEDIUM_HIGH_PRESSURE_SIDE"],"BOTH")
        self.assertEqual(b["LATE_TITLE_NEAR_3_SIDE"],"HOME_ONLY")
        self.assertEqual(b["LATE_TITLE_NEAR_6_SIDE"],"HOME_ONLY")
        self.assertEqual(b["LATE_SURVIVAL_DANGER_SIDE"],"AWAY_ONLY")
        self.assertEqual(b["LATE_SURVIVAL_WITHIN_3_SIDE"],"BOTH")
        self.assertEqual(b["LATE_SURVIVAL_WITHIN_6_SIDE"],"BOTH")
        self.assertEqual(b["DRAW_TITLE_PATH_SIDE"],"HOME_ONLY")
        self.assertEqual(b["DRAW_SAFE_PATH_SIDE"],"AWAY_ONLY")

    def test_early_season_is_neither_not_unknown(self):
        row=context()
        row["home_season_phase"]="MID"
        row["away_season_phase"]="EARLY"
        b=r.factor_buckets(row)
        self.assertEqual(b["LATE_TITLE_NEAR_3_SIDE"],"NEITHER")
        self.assertEqual(b["LATE_SURVIVAL_DANGER_SIDE"],"NEITHER")
        self.assertEqual(b["LATE_SURVIVAL_WITHIN_6_SIDE"],"NEITHER")

    def test_incomplete_table_fails_to_unknown_buckets(self):
        row=context()
        row["full_table_available"]="false"
        b=r.factor_buckets(row)
        self.assertEqual(set(b),set(r.FACTOR_NAMES))
        self.assertTrue(all(v=="UNKNOWN" for v in b.values()))

    def test_europe_or_authority_leak_invalidates_context(self):
        row=context()
        self.assertTrue(r.valid_context(row))
        row["europe_status"]="CHAMPIONS_LEAGUE"
        self.assertFalse(r.valid_context(row))
        row=context()
        row["operational_betting_authority"]="true"
        self.assertFalse(r.valid_context(row))

    def test_enrich_uses_closing_market_benchmark(self):
        joined,diag=r.enrich([match()],[context()])
        self.assertEqual(diag["joined_rows"],1)
        self.assertEqual(diag["invalid_context_governance_rows"],0)
        self.assertEqual(len(joined),1)
        self.assertEqual(joined[0]["_1x2_source"],"AVG_CLOSE")
        self.assertEqual(joined[0]["_tot_source"],"AVG_CLOSE")
        self.assertAlmostEqual(sum(joined[0]["_1x2_novig"]),1.0,places=6)

    def test_aggregate_exposes_all_declared_factors_without_authority(self):
        joined,diag=r.enrich([match()],[context()])
        self.assertEqual(diag["joined_rows"],1)
        profiles=r.aggregate(joined)
        factors={x["factor"] for x in profiles}
        self.assertEqual(factors,set(r.FACTOR_NAMES))
        self.assertTrue(all(x["research_only"]=="true" for x in profiles))
        self.assertTrue(all(x["operational_betting_authority"]=="false" for x in profiles))
        self.assertTrue(all(x["creates_signal"]=="false" for x in profiles))

    def test_small_sample_stability_remains_descriptive(self):
        rows=[]
        for season in ("2023/2024","2024/2025"):
            c=context("m"+season)
            c["season_label"]=season
            j,_=r.enrich([match("m"+season)],[c])
            rows.extend(j)
        stable=r.stability(rows)
        self.assertTrue(stable)
        self.assertTrue(all(x["research_only"]=="true" for x in stable))
        self.assertTrue(all(x["operational_betting_authority"]=="false" for x in stable))


if __name__=="__main__":
    unittest.main()
