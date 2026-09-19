import unittest

from scripts import stage80_pbk14_international_window_market_research as r


def base_row():
    return {
        "historical_match_id":"m1","api_fixture_id":"100","mapping_status":"AUTO",
        "fuzzy_string_matching_used":"false","one_to_one_verified":"true",
        "window_reference_contract":"NEAREST_WINDOW_RELATION_GATED_V2",
        "window_relation":"AFTER","hours_to_window_start":"","hours_since_window_end":"62",
        "within_72h_before_window":"false","within_96h_before_window":"false",
        "within_7d_before_window":"false","within_72h_after_window":"true",
        "within_96h_after_window":"true","within_7d_after_window":"true",
        "home_first_domestic_league_match_after_window":"true",
        "away_first_domestic_league_match_after_window":"false",
        "window_max_matches":"2",
        "player_level_international_status":"UNVERIFIED",
        "calendar_level_only":"true","as_known_calendar_reference":"true",
        "no_match_result_dependency":"true","no_lookahead":"true","context_provider_calls":"0",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
        "league_code":"E0","season_start":"2024","date_iso":"2024-09-14",
        "ft_result":"H","ft_home_goals":"2","ft_away_goals":"1",
        "avg_close_home":"2.00","avg_close_draw":"3.50","avg_close_away":"4.00",
        "avg_close_over_25":"1.90","avg_close_under_25":"1.95",
    }


class PBK14InternationalWindowMarketResearchTests(unittest.TestCase):
    def test_after_62h_and_home_first_are_bucketed(self):
        b=r.factor_buckets(base_row())
        self.assertEqual(b["WINDOW_RELATION"],"AFTER")
        self.assertEqual(b["BEFORE_WINDOW_BAND"],"NOT_BEFORE")
        self.assertEqual(b["AFTER_WINDOW_BAND"],"WITHIN_72H")
        self.assertEqual(b["FIRST_DOMESTIC_AFTER_WINDOW_SIDE"],"HOME_ONLY")
        self.assertEqual(b["WINDOW_MAX_MATCHES"],"2")

    def test_distance_bands_are_mutually_interpretable(self):
        row=base_row()
        row["window_relation"]="BEFORE"
        row["hours_since_window_end"]=""
        row["hours_to_window_start"]="80"
        row["home_first_domestic_league_match_after_window"]="false"
        b=r.factor_buckets(row)
        self.assertEqual(b["BEFORE_WINDOW_BAND"],"72_96H")
        self.assertEqual(b["AFTER_WINDOW_BAND"],"NOT_AFTER")
        self.assertEqual(b["FIRST_DOMESTIC_AFTER_WINDOW_SIDE"],"NEITHER")

        row["hours_to_window_start"]="120"
        self.assertEqual(r.factor_buckets(row)["BEFORE_WINDOW_BAND"],"96H_7D")
        row["hours_to_window_start"]="200"
        self.assertEqual(r.factor_buckets(row)["BEFORE_WINDOW_BAND"],"BEYOND_7D")

    def test_inside_is_explicit_without_fake_after_distance(self):
        row=base_row()
        row["window_relation"]="INSIDE"
        row["hours_since_window_end"]=""
        row["home_first_domestic_league_match_after_window"]="false"
        b=r.factor_buckets(row)
        self.assertEqual(b["WINDOW_RELATION"],"INSIDE")
        self.assertEqual(b["BEFORE_WINDOW_BAND"],"NOT_BEFORE")
        self.assertEqual(b["AFTER_WINDOW_BAND"],"NOT_AFTER")

    def test_v1_or_player_inference_is_fail_closed(self):
        row=base_row()
        row["window_reference_contract"]=""
        self.assertFalse(r.valid_row(row))
        row=base_row()
        row["player_level_international_status"]="CONFIRMED"
        self.assertFalse(r.valid_row(row))

    def test_enrich_summary_uses_closing_market_only(self):
        joined,invalid=r.enrich([base_row()])
        self.assertEqual(invalid,0)
        self.assertEqual(len(joined),1)
        summary=r.summarize(joined,"AFTER_WINDOW_BAND","WITHIN_72H","ALL","ALL")
        self.assertEqual(summary["matches"],1)
        self.assertEqual(summary["closing_1x2_matches"],1)
        self.assertEqual(summary["closing_total25_matches"],1)
        self.assertAlmostEqual(float(summary["home_flat_bet_roi_pct"]),100.0,places=3)
        self.assertAlmostEqual(float(summary["over25_flat_bet_roi_pct"]),90.0,places=3)
        self.assertEqual(summary["promotes_factor"],"false")
        self.assertEqual(summary["operational_betting_authority"],"false")

    def test_aggregate_contains_all_factors(self):
        joined,invalid=r.enrich([base_row()])
        self.assertEqual(invalid,0)
        factors={x["factor"] for x in r.aggregate(joined)}
        self.assertEqual(factors,set(r.FACTORS))

    def test_stability_never_promotes(self):
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
