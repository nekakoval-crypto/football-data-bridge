import unittest

from scripts import stage80_pbk14_congestion_market_research as r


def base_row():
    return {
        "historical_match_id":"m1","api_fixture_id":"100","mapping_status":"AUTO",
        "fuzzy_string_matching_used":"false","one_to_one_verified":"true",
        "strictly_prior_fixture_evidence_only":"true","future_schedule_used":"false",
        "no_lookahead":"true","historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
        "league_code":"E0","season_start":"2024","date_iso":"2024-09-15",
        "ft_result":"H","ft_home_goals":"2","ft_away_goals":"1",
        "avg_close_home":"2.00","avg_close_draw":"3.50","avg_close_away":"4.00",
        "avg_close_over_25":"1.90","avg_close_under_25":"1.95",
        "home_hours_since_prev_nonleague":"68",
        "home_prev_nonleague_was_uefa":"true",
        "home_prev_nonleague_was_domestic_cup":"false",
        "home_prev_nonleague_was_thursday":"true",
        "away_hours_since_prev_nonleague":"",
        "away_prev_nonleague_was_uefa":"false",
        "away_prev_nonleague_was_domestic_cup":"false",
        "away_prev_nonleague_was_thursday":"false",
    }


class PBK14CongestionMarketResearchTests(unittest.TestCase):
    def test_factor_buckets_capture_home_only_uefa_and_thursday_to_weekend(self):
        row=base_row()
        buckets=r.factor_buckets(row)
        self.assertEqual(buckets["NONLEAGUE_72H_SIDE"],"HOME_ONLY")
        self.assertEqual(buckets["UEFA_72H_SIDE"],"HOME_ONLY")
        self.assertEqual(buckets["UEFA_96H_SIDE"],"HOME_ONLY")
        self.assertEqual(buckets["DOMESTIC_CUP_72H_SIDE"],"NEITHER")
        self.assertEqual(buckets["PREV_NONLEAGUE_THURSDAY_SIDE"],"HOME_ONLY")
        self.assertEqual(buckets["THURSDAY_TO_WEEKEND_SIDE"],"HOME_ONLY")

    def test_thursday_to_weekend_distinguishes_non_weekend_fixture(self):
        row=base_row()
        row["date_iso"]="2024-09-16"
        buckets=r.factor_buckets(row)
        self.assertEqual(buckets["PREV_NONLEAGUE_THURSDAY_SIDE"],"HOME_ONLY")
        self.assertEqual(buckets["THURSDAY_TO_WEEKEND_SIDE"],"NOT_WEEKEND_FIXTURE")

    def test_review_or_fuzzy_rows_are_invalid(self):
        row=base_row()
        row["mapping_status"]="REVIEW"
        self.assertFalse(r.valid_row(row))
        row=base_row()
        row["fuzzy_string_matching_used"]="true"
        self.assertFalse(r.valid_row(row))

    def test_enrich_and_summary_use_closing_market_only(self):
        row=base_row()
        joined,invalid=r.enrich([row])
        self.assertEqual(invalid,0)
        self.assertEqual(len(joined),1)
        summary=r.summarize(joined,"UEFA_72H_SIDE","HOME_ONLY","ALL","ALL")
        self.assertEqual(summary["matches"],1)
        self.assertEqual(summary["home_wins"],1)
        self.assertEqual(summary["closing_1x2_matches"],1)
        self.assertEqual(summary["closing_total25_matches"],1)
        self.assertAlmostEqual(float(summary["home_flat_bet_roi_pct"]),100.0,places=3)
        self.assertAlmostEqual(float(summary["over25_flat_bet_roi_pct"]),90.0,places=3)
        self.assertEqual(summary["research_only"],"true")
        self.assertEqual(summary["operational_betting_authority"],"false")
        self.assertEqual(summary["promotes_factor"],"false")

    def test_side_bucket_both_and_neither(self):
        self.assertEqual(r.side_bucket(True,True),"BOTH")
        self.assertEqual(r.side_bucket(False,False),"NEITHER")
        self.assertEqual(r.side_bucket(False,True),"AWAY_ONLY")

    def test_aggregate_contains_all_declared_factors(self):
        joined,invalid=r.enrich([base_row()])
        self.assertEqual(invalid,0)
        profiles=r.aggregate(joined)
        factors={x["factor"] for x in profiles}
        self.assertEqual(factors,set(r.FACTORS))

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
