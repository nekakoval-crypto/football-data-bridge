import unittest

from scripts import stage80_pbk14_congestion_market_join as j


def market(mid="m1"):
    return {
        "historical_match_id":mid,"league_code":"E0","league_name":"Premier League",
        "country":"England","season_label":"2024/2025","date_iso":"2024-08-10",
        "time_local":"15:00","home_team":"Alpha","away_team":"Beta",
        "ft_home_goals":"2","ft_away_goals":"1","ft_result":"H",
        "avg_close_home":"2.00","avg_close_draw":"3.50","avg_close_away":"4.00",
        "avg_close_over_25":"1.90","avg_close_under_25":"1.95",
    }


def bridge(mid="m1",fid="100",status="AUTO"):
    return {
        "historical_match_id":mid,"api_fixture_id":fid,"mapping_status":status,
        "mapping_reason":"EXACT_DATE_TEAMS_SCORE_UNIQUE","provider_league_id":"39",
        "season_start":"2024","api_kickoff_utc":"2024-08-10T14:00:00+00:00",
        "fuzzy_string_matching_used":"false","one_to_one_verified":"true",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
    }


def congestion(fid="100"):
    return {
        "domestic_fixture_id":fid,
        "home_prev_nonleague_fixture_id":"90",
        "home_prev_nonleague_competition_name":"UEFA Europa League",
        "home_prev_nonleague_competition_role":"UEFA",
        "home_hours_since_prev_nonleague":"68",
        "home_prev_nonleague_was_thursday":"true",
        "home_prev_nonleague_was_uefa":"true",
        "home_prev_nonleague_was_domestic_cup":"false",
        "home_nonleague_matches_prev_7d":"1","home_nonleague_matches_prev_14d":"1",
        "home_uefa_matches_prev_7d":"1","home_domestic_cup_matches_prev_7d":"0",
        "away_nonleague_matches_prev_7d":"0","away_nonleague_matches_prev_14d":"0",
        "away_uefa_matches_prev_7d":"0","away_domestic_cup_matches_prev_7d":"0",
        "either_team_prev_nonleague_within_72h":"true",
        "either_team_prev_nonleague_within_96h":"true",
        "either_team_prev_uefa_within_72h":"true",
        "either_team_prev_uefa_within_96h":"true",
        "either_team_prev_domestic_cup_within_72h":"false",
        "either_team_prev_domestic_cup_within_96h":"false",
        "either_team_previous_nonleague_was_thursday":"true",
        "strictly_prior_fixture_evidence_only":"true",
        "future_schedule_used":"false","no_lookahead":"true",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
    }


class PBK14CongestionMarketJoinTests(unittest.TestCase):
    def test_auto_high_join_is_exact_and_no_lookahead(self):
        rows,diag=j.project([market()],[bridge()],[congestion()])
        self.assertEqual(diag["joined_rows"],1)
        self.assertEqual(diag["missing_market_rows"],0)
        self.assertEqual(diag["missing_congestion_rows"],0)
        row=rows[0]
        self.assertEqual(row["historical_match_id"],"m1")
        self.assertEqual(row["api_fixture_id"],"100")
        self.assertEqual(row["mapping_status"],"AUTO")
        self.assertEqual(row["either_team_prev_uefa_within_72h"],"true")
        self.assertEqual(row["home_hours_since_prev_nonleague"],"68")
        self.assertEqual(row["strictly_prior_fixture_evidence_only"],"true")
        self.assertEqual(row["future_schedule_used"],"false")
        self.assertEqual(row["no_lookahead"],"true")
        self.assertEqual(row["fuzzy_string_matching_used"],"false")
        self.assertEqual(row["operational_betting_authority"],"false")

    def test_review_and_unmapped_never_enter_join(self):
        b1=bridge("m1","100","REVIEW")
        b2=bridge("m2","101","UNMAPPED")
        rows,diag=j.project(
            [market("m1"),market("m2")],
            [b1,b2],
            [congestion("100"),congestion("101")],
        )
        self.assertEqual(rows,[])
        self.assertEqual(diag["bridge_eligible_rows"],0)

    def test_missing_congestion_is_explicit_not_synthetic_zero(self):
        rows,diag=j.project([market()],[bridge()],[])
        self.assertEqual(rows,[])
        self.assertEqual(diag["missing_congestion_rows"],1)
        self.assertEqual(diag["missing_market_rows"],0)

    def test_invalid_bridge_governance_is_excluded(self):
        b=bridge()
        b["fuzzy_string_matching_used"]="true"
        rows,diag=j.project([market()],[b],[congestion()])
        self.assertEqual(rows,[])
        self.assertEqual(diag["bridge_eligible_rows"],0)

    def test_duplicate_provider_fixture_identity_is_detected(self):
        b1=bridge("m1","100","AUTO")
        b2=bridge("m2","100","HIGH")
        rows,diag=j.project(
            [market("m1"),market("m2")],
            [b1,b2],
            [congestion("100")],
        )
        self.assertEqual(diag["bridge_eligible_duplicate_api_fixture_ids"],1)
        self.assertEqual(len(rows),2)

    def test_meta_reports_market_coverage_without_granting_authority(self):
        rows,diag=j.project([market()],[bridge()],[congestion()])
        meta=j.build_meta(rows,diag)
        self.assertEqual(meta["closing_1x2_matches"],1)
        self.assertEqual(meta["closing_total25_matches"],1)
        self.assertEqual(meta["rows_either_prev_uefa_72h"],1)
        self.assertEqual(meta["join_coverage_pct"],100.0)
        self.assertTrue(meta["review_unmapped_excluded"])
        self.assertFalse(meta["fuzzy_string_matching_used"])
        self.assertFalse(meta["operational_betting_authority"])
        self.assertFalse(meta["creates_signal"])


if __name__=="__main__":
    unittest.main()
