import unittest

from scripts.stage80_prematch_factor_research import enrich
from scripts.stage80_prematch_factor_walkforward import build_folds, summarize_folds


def ctx(mid,season):
    return {
        "historical_match_id":mid,"league_code":"E0","season_label":season,
        "is_monday":"true","is_thursday":"false","is_weekend":"false",
        "kickoff_minutes_local":"1020",
        "home_rest_days":"6","away_rest_days":"4",
        "home_matches_prev_7d":"0","away_matches_prev_7d":"0",
        "home_rank_pre":"2","away_rank_pre":"10",
        "home_form_matches_last5":"5","away_form_matches_last5":"5",
        "home_ppg_last5":"2.0","away_ppg_last5":"1.0",
        "home_home_matches_last5":"5","away_away_matches_last5":"5",
        "home_home_ppg_last5":"2.0","away_away_ppg_last5":"1.0",
        "same_day_results_excluded":"true","no_lookahead":"true",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
    }


def match(mid,result):
    if result=="H":
        hg,ag="2","1"
    else:
        hg,ag="0","1"
    return {
        "historical_match_id":mid,"ft_result":result,
        "ft_home_goals":hg,"ft_away_goals":ag,
        "avg_close_home":"2.0","avg_close_draw":"4.0","avg_close_away":"4.0",
        "avg_close_over_25":"2.0","avg_close_under_25":"2.0",
    }


class Stage80PrematchFactorWalkforwardTests(unittest.TestCase):
    def test_walkforward_uses_only_prior_seasons_and_records_sign_persistence(self):
        matches=[]; contexts=[]; idx=0
        for season,count,result in (
            ("2017/2018",120,"H"),
            ("2018/2019",120,"H"),
            ("2019/2020",40,"A"),
        ):
            for _ in range(count):
                idx+=1; mid=f"m{idx}"
                matches.append(match(mid,result))
                contexts.append(ctx(mid,season))

        joined,diag=enrich(matches,contexts)
        self.assertEqual(diag["joined_rows"],280)
        folds=build_folds(joined)

        home=next(
            r for r in folds
            if r["factor"]=="WEEKDAY"
            and r["bucket"]=="MONDAY"
            and r["scope_type"]=="ALL"
            and r["target"]=="HOME"
            and r["test_season"]=="2019/2020"
        )
        self.assertEqual(home["train_first_season"],"2017/2018")
        self.assertEqual(home["train_last_season"],"2018/2019")
        self.assertEqual(home["train_seasons"],2)
        self.assertEqual(home["train_market_matches"],240)
        self.assertEqual(home["test_market_matches"],40)
        self.assertEqual(home["sample_threshold_pass"],"true")
        self.assertEqual(home["train_calibration_sign"],"POSITIVE")
        self.assertEqual(home["test_calibration_sign"],"NEGATIVE")
        self.assertEqual(home["calibration_sign_persists"],"false")
        self.assertEqual(home["train_roi_sign"],"POSITIVE")
        self.assertEqual(home["test_roi_sign"],"NEGATIVE")
        self.assertEqual(home["roi_sign_persists"],"false")
        self.assertEqual(home["operational_betting_authority"],"false")

        # 2018/19 is not emitted: it has only one prior season.
        self.assertFalse(any(
            r["factor"]=="WEEKDAY" and r["bucket"]=="MONDAY"
            and r["scope_type"]=="ALL" and r["target"]=="HOME"
            and r["test_season"]=="2018/2019"
            for r in folds
        ))

        summary=summarize_folds(folds)
        home_summary=next(
            r for r in summary
            if r["factor"]=="WEEKDAY"
            and r["bucket"]=="MONDAY"
            and r["scope_type"]=="ALL"
            and r["target"]=="HOME"
        )
        self.assertEqual(home_summary["sample_threshold_pass_folds"],1)
        self.assertEqual(home_summary["calibration_sign_persistent_folds"],0)
        self.assertEqual(home_summary["roi_sign_persistent_folds"],0)
        self.assertEqual(home_summary["promotes_factor"],"false")
        self.assertEqual(home_summary["creates_signal"],"false")


if __name__=="__main__":
    unittest.main()
