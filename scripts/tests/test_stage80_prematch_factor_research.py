import unittest

from scripts.stage80_prematch_factor_research import aggregate, enrich, factor_buckets, stability


def context(mid, season="2025/2026", league="E0", **extra):
    row={
        "historical_match_id":mid,
        "league_code":league,
        "season_label":season,
        "is_monday":"true","is_thursday":"false","is_weekend":"false",
        "kickoff_minutes_local":"1020",
        "home_rest_days":"6","away_rest_days":"2",
        "home_matches_prev_7d":"1","away_matches_prev_7d":"0",
        "home_rank_pre":"2","away_rank_pre":"10",
        "home_form_matches_last5":"5","away_form_matches_last5":"5",
        "home_ppg_last5":"2.2","away_ppg_last5":"1.0",
        "home_home_matches_last5":"5","away_away_matches_last5":"5",
        "home_home_ppg_last5":"2.4","away_away_ppg_last5":"0.8",
        "same_day_results_excluded":"true","no_lookahead":"true",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
    }
    row.update(extra)
    return row


def match(mid,result="H",hg="2",ag="1"):
    return {
        "historical_match_id":mid,
        "ft_result":result,"ft_home_goals":hg,"ft_away_goals":ag,
        "avg_close_home":"2.0","avg_close_draw":"4.0","avg_close_away":"4.0",
        "b365_close_home":"1.9","b365_close_draw":"3.9","b365_close_away":"4.1",
        "avg_close_over_25":"2.0","avg_close_under_25":"2.0",
        "b365_close_over_25":"1.95","b365_close_under_25":"1.95",
    }


class Stage80PrematchFactorResearchTests(unittest.TestCase):
    def test_factor_buckets_are_deterministic(self):
        b=factor_buckets(context("m1"))
        self.assertEqual(b["WEEKDAY"],"MONDAY")
        self.assertEqual(b["KICKOFF_LOCAL"],"15_00_17_59")
        self.assertEqual(b["SHORT_REST"],"AWAY_SHORT_ONLY")
        self.assertEqual(b["REST_ADVANTAGE"],"HOME_3PLUS")
        self.assertEqual(b["CONGESTION_7D_DIFF"],"HOME_MORE")
        self.assertEqual(b["TABLE_RANK_DIFF"],"HOME_5PLUS_BETTER")
        self.assertEqual(b["FORM5_PPG_DIFF"],"HOME_075PLUS_BETTER")
        self.assertEqual(b["VENUE_FORM5_PPG_DIFF"],"HOME_075PLUS_BETTER")

    def test_market_metrics_use_closing_no_vig_not_pbk_probability(self):
        joined,diag=enrich([match("m1")],[context("m1")])
        self.assertEqual(diag["joined_rows"],1)
        rows=aggregate(joined)
        monday=next(
            r for r in rows
            if r["factor"]=="WEEKDAY" and r["bucket"]=="MONDAY"
            and r["scope_type"]=="ALL"
        )
        self.assertEqual(monday["matches"],1)
        self.assertEqual(monday["closing_1x2_matches"],1)
        self.assertEqual(monday["closing_1x2_avg_source_rows"],1)
        self.assertEqual(monday["avg_market_novig_home"],0.5)
        self.assertEqual(monday["home_flat_bet_roi_pct"],100.0)
        self.assertEqual(monday["home_calibration_pp"],50.0)
        self.assertEqual(monday["closing_total25_matches"],1)
        self.assertEqual(monday["over25_flat_bet_roi_pct"],100.0)
        self.assertEqual(monday["over25_calibration_pp"],50.0)
        self.assertEqual(monday["research_only"],"true")
        self.assertEqual(monday["operational_betting_authority"],"false")

    def test_invalid_governance_context_is_not_joined(self):
        bad=context("m1",no_lookahead="false")
        joined,diag=enrich([match("m1")],[bad])
        self.assertEqual(joined,[])
        self.assertEqual(diag["invalid_context_governance_rows"],1)
        self.assertEqual(diag["joined_rows"],0)

    def test_season_stability_counts_observed_positive_roi_without_ranking(self):
        matches=[
            match("m1","H","2","1"),
            match("m2","A","0","1"),
        ]
        contexts=[
            context("m1","2024/2025"),
            context("m2","2025/2026"),
        ]
        joined,_=enrich(matches,contexts)
        rows=stability(joined)
        monday=next(
            r for r in rows
            if r["factor"]=="WEEKDAY" and r["bucket"]=="MONDAY"
            and r["scope_type"]=="ALL"
        )
        self.assertEqual(monday["seasons_with_matches"],2)
        self.assertEqual(monday["home_roi_observed_seasons"],2)
        self.assertEqual(monday["home_roi_positive_seasons"],1)
        self.assertEqual(monday["research_only"],"true")
        self.assertEqual(monday["creates_signal"],"false")


if __name__=="__main__":
    unittest.main()
