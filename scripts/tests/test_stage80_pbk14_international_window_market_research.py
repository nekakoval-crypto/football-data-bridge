import unittest

from scripts import stage80_pbk14_international_window_market_research as r


def base_row():
    return {
        "historical_match_id":"m1",
        "api_fixture_id":"100",
        "mapping_status":"AUTO",
        "fuzzy_string_matching_used":"false",
        "one_to_one_verified":"true",
        "window_reference_contract":"NEAREST_WINDOW_RELATION_GATED_V2",
        "player_level_international_status":"UNVERIFIED",
        "final_tournaments_included":"false",
        "non_uefa_only_windows_included":"false",
        "calendar_level_only":"true",
        "as_known_calendar_reference":"true",
        "no_match_result_dependency":"true",
        "no_lookahead":"true",
        "context_provider_calls":"0",
        "historical_backfill_only":"true",
        "research_only":"true",
        "operational_betting_authority":"false",
        "creates_signal":"false",
        "probability_mutation":"false",
        "eligibility_mutation":"false",
        "stake_changes":"false",
        "forward_journal_mutation":"false",
        "league_code":"E0",
        "season_start":"2024",
        "date_iso":"2024-09-14",
        "ft_result":"H",
        "ft_home_goals":"2",
        "ft_away_goals":"1",
        "avg_close_home":"2.00",
        "avg_close_draw":"3.50",
        "avg_close_away":"4.00",
        "avg_close_over_25":"1.90",
        "avg_close_under_25":"1.95",
        "window_relation":"AFTER",
        "window_max_matches":"2",
        "within_72h_before_window":"false",
        "within_96h_before_window":"false",
        "within_7d_before_window":"false",
        "within_72h_after_window":"true",
        "within_96h_after_window":"true",
        "within_7d_after_window":"true",
        "home_first_domestic_league_match_after_window":"true",
        "away_first_domestic_league_match_after_window":"false",
    }


class PBK14InternationalWindowMarketResearchTests(unittest.TestCase):
    def test_factor_buckets_capture_post_window_and_first_side(self):
        buckets=r.factor_buckets(base_row())
        self.assertEqual(buckets["INTL_BEFORE_72H"],"OUTSIDE")
        self.assertEqual(buckets["INTL_AFTER_72H"],"WITHIN")
        self.assertEqual(buckets["INTL_AFTER_96H"],"WITHIN")
        self.assertEqual(buckets["INTL_AFTER_7D"],"WITHIN")
        self.assertEqual(buckets["FIRST_DOMESTIC_AFTER_SIDE"],"HOME_ONLY")
        self.assertEqual(buckets["WINDOW_RELATION"],"AFTER")
        self.assertEqual(buckets["WINDOW_MAX_MATCHES"],"MAX_2")

    def test_first_after_side_supports_both_and_neither(self):
        row=base_row()
        row["away_first_domestic_league_match_after_window"]="true"
        self.assertEqual(r.factor_buckets(row)["FIRST_DOMESTIC_AFTER_SIDE"],"BOTH")
        row["home_first_domestic_league_match_after_window"]="false"
        row["away_first_domestic_league_match_after_window"]="false"
        self.assertEqual(r.factor_buckets(row)["FIRST_DOMESTIC_AFTER_SIDE"],"NEITHER")

    def test_before_inside_and_window_length_are_calendar_only(self):
        row=base_row()
        row.update({
            "window_relation":"INSIDE",
            "window_max_matches":"3",
            "within_72h_after_window":"false",
            "within_96h_after_window":"false",
            "within_7d_after_window":"false",
            "home_first_domestic_league_match_after_window":"false",
        })
        buckets=r.factor_buckets(row)
        self.assertEqual(buckets["WINDOW_RELATION"],"INSIDE")
        self.assertEqual(buckets["WINDOW_MAX_MATCHES"],"MAX_3")
        self.assertEqual(buckets["INTL_AFTER_72H"],"OUTSIDE")
        self.assertEqual(buckets["FIRST_DOMESTIC_AFTER_SIDE"],"NEITHER")

    def test_review_fuzzy_old_contract_or_player_promotion_are_invalid(self):
        row=base_row()
        row["mapping_status"]="REVIEW"
        self.assertFalse(r.valid_row(row))
        row=base_row()
        row["fuzzy_string_matching_used"]="true"
        self.assertFalse(r.valid_row(row))
        row=base_row()
        row["window_reference_contract"]="OLD"
        self.assertFalse(r.valid_row(row))
        row=base_row()
        row["player_level_international_status"]="CONFIRMED"
        self.assertFalse(r.valid_row(row))

    def test_enrich_and_summary_use_closing_market_only(self):
        joined,invalid=r.enrich([base_row()])
        self.assertEqual(invalid,0)
        self.assertEqual(len(joined),1)
        summary=r.summarize(joined,"INTL_AFTER_72H","WITHIN","ALL","ALL")
        self.assertEqual(summary["matches"],1)
        self.assertEqual(summary["home_wins"],1)
        self.assertEqual(summary["closing_1x2_matches"],1)
        self.assertEqual(summary["closing_total25_matches"],1)
        self.assertAlmostEqual(float(summary["home_flat_bet_roi_pct"]),100.0,places=3)
        self.assertAlmostEqual(float(summary["over25_flat_bet_roi_pct"]),90.0,places=3)
        self.assertEqual(summary["research_only"],"true")
        self.assertEqual(summary["operational_betting_authority"],"false")
        self.assertEqual(summary["promotes_factor"],"false")

    def test_aggregate_contains_all_declared_factors(self):
        joined,invalid=r.enrich([base_row()])
        self.assertEqual(invalid,0)
        profiles=r.aggregate(joined)
        self.assertEqual({x["factor"] for x in profiles},set(r.FACTORS))

    def test_stability_never_promotes_factor(self):
        rows=[]
        for season in ("2023","2024"):
            row=base_row()
            row["historical_match_id"]="m"+season
            row["api_fixture_id"]="f"+season
            row["season_start"]=season
            rows.append(row)
        joined,invalid=r.enrich(rows)
        self.assertEqual(invalid,0)
        stable=r.stability(joined)
        self.assertTrue(stable)
        self.assertTrue(all(x["promotes_factor"]=="false" for x in stable))
        self.assertTrue(all(x["operational_betting_authority"]=="false" for x in stable))


if __name__=="__main__":
    unittest.main()
