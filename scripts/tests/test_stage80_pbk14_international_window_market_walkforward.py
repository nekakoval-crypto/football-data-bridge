import unittest

from scripts import stage80_pbk14_international_window_market_walkforward as w
from scripts import stage80_pbk14_international_window_market_research as r


def row(mid,season,result="H",home_odds="2.0",draw_odds="3.5",away_odds="4.0"):
    return {
        "historical_match_id":mid,"api_fixture_id":"f"+mid,"mapping_status":"AUTO",
        "fuzzy_string_matching_used":"false","one_to_one_verified":"true",
        "window_reference_contract":"NEAREST_WINDOW_RELATION_GATED_V2",
        "player_level_international_status":"UNVERIFIED",
        "final_tournaments_included":"false","non_uefa_only_windows_included":"false",
        "calendar_level_only":"true","as_known_calendar_reference":"true",
        "no_match_result_dependency":"true","no_lookahead":"true","context_provider_calls":"0",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
        "league_code":"E0","season_start":str(season),"date_iso":f"{season}-09-15",
        "ft_result":result,"ft_home_goals":"2","ft_away_goals":"1",
        "avg_close_home":home_odds,"avg_close_draw":draw_odds,"avg_close_away":away_odds,
        "avg_close_over_25":"1.90","avg_close_under_25":"1.95",
        "window_relation":"BEFORE","window_max_matches":"2",
        "within_72h_before_window":"true","within_96h_before_window":"true",
        "within_7d_before_window":"true","within_72h_after_window":"false",
        "within_96h_after_window":"false","within_7d_after_window":"false",
        "home_first_domestic_league_match_after_window":"false",
        "away_first_domestic_league_match_after_window":"false",
    }


class PBK14InternationalWindowMarketWalkforwardTests(unittest.TestCase):
    def test_target_metrics_uses_market_novig_not_pbk_probability(self):
        joined,invalid=r.enrich([row("1",2024)])
        self.assertEqual(invalid,0)
        m=w.target_metrics(joined,"HOME")
        self.assertEqual(m["matches"],1)
        self.assertAlmostEqual(m["hit_rate"],1.0,places=6)
        self.assertGreater(m["market_novig"],0)
        self.assertGreater(m["roi_pct"],0)

    def test_build_folds_uses_only_prior_seasons(self):
        raw=[]
        for season in (2017,2018,2019):
            for i in range(40):
                raw.append(row(f"{season}-{i}",season))
        joined,invalid=r.enrich(raw)
        self.assertEqual(invalid,0)
        old_train=w.MIN_TRAIN_MARKET_MATCHES
        old_test=w.MIN_TEST_MARKET_MATCHES
        try:
            w.MIN_TRAIN_MARKET_MATCHES=10
            w.MIN_TEST_MARKET_MATCHES=10
            folds=w.build_folds(joined)
        finally:
            w.MIN_TRAIN_MARKET_MATCHES=old_train
            w.MIN_TEST_MARKET_MATCHES=old_test
        eligible=[x for x in folds if x["sample_threshold_pass"]=="true"]
        self.assertTrue(eligible)
        fold=next(
            x for x in eligible
            if x["test_season"]=="2019"
            and x["factor"]=="INTL_BEFORE_72H"
            and x["bucket"]=="WITHIN"
            and x["target"]=="HOME"
        )
        self.assertEqual(fold["train_first_season"],"2017")
        self.assertEqual(fold["train_last_season"],"2018")
        self.assertEqual(fold["train_seasons"],2)

    def test_no_fold_before_two_prior_seasons(self):
        raw=[]
        for season in (2017,2018):
            for i in range(40):
                raw.append(row(f"{season}-{i}",season))
        joined,invalid=r.enrich(raw)
        self.assertEqual(invalid,0)
        self.assertEqual(w.build_folds(joined),[])

    def test_summary_never_promotes_factor(self):
        folds=[{
            "factor":"INTL_BEFORE_72H","bucket":"WITHIN",
            "scope_type":"ALL","scope_value":"ALL",
            "target":"HOME","test_season":"2019","train_market_matches":"100",
            "test_market_matches":"30","sample_threshold_pass":"true",
            "train_calibration_sign":"POSITIVE","test_calibration_sign":"POSITIVE",
            "calibration_sign_persists":"true","train_roi_sign":"NEGATIVE",
            "test_roi_sign":"NEGATIVE","roi_sign_persists":"true",
            "test_calibration_pp":"1.0","test_flat_bet_roi_pct":"-2.0",
        }]
        summary=w.summarize_folds(folds)
        self.assertEqual(len(summary),1)
        self.assertEqual(summary[0]["promotes_factor"],"false")
        self.assertEqual(summary[0]["operational_betting_authority"],"false")

    def test_sign_has_neutral_band(self):
        self.assertEqual(w.sign(0.1,0.25),"NEUTRAL")
        self.assertEqual(w.sign(0.3,0.25),"POSITIVE")
        self.assertEqual(w.sign(-0.3,0.25),"NEGATIVE")


if __name__=="__main__":
    unittest.main()
