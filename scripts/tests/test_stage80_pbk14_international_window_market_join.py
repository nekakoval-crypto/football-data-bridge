import unittest

from scripts import stage80_pbk14_international_window_market_join as j


def market(mid="m1"):
    return {
        "historical_match_id": mid,
        "league_code": "E0",
        "league_name": "Premier League",
        "country": "England",
        "season_label": "2024/2025",
        "date_iso": "2024-09-14",
        "time_local": "15:00",
        "home_team": "Alpha",
        "away_team": "Beta",
        "ft_home_goals": "2",
        "ft_away_goals": "1",
        "ft_result": "H",
        "avg_close_home": "2.00",
        "avg_close_draw": "3.50",
        "avg_close_away": "4.00",
        "avg_close_over_25": "1.90",
        "avg_close_under_25": "1.95",
    }


def bridge(mid="m1", fid="100", status="AUTO"):
    return {
        "historical_match_id": mid,
        "api_fixture_id": fid,
        "mapping_status": status,
        "mapping_reason": "EXACT_DATE_TEAMS_SCORE_UNIQUE",
        "provider_league_id": "39",
        "season_start": "2024",
        "api_kickoff_utc": "2024-09-14T14:00:00+00:00",
        "fuzzy_string_matching_used": "false",
        "one_to_one_verified": "true",
        "historical_backfill_only": "true",
        "research_only": "true",
        "operational_betting_authority": "false",
        "creates_signal": "false",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }


def context(fid="100"):
    return {
        "domestic_fixture_id": fid,
        "nearest_window_id": "2024_SEP",
        "window_start_utc": "2024-09-02T00:00:00Z",
        "window_end_utc": "2024-09-10T23:59:59Z",
        "window_max_matches": "2",
        "window_notes": "UEFA-relevant international window",
        "window_relation": "AFTER",
        "window_reference_contract": "NEAREST_WINDOW_RELATION_GATED_V2",
        "hours_to_window_start": "",
        "hours_since_window_end": "62.0",
        "within_72h_before_window": "false",
        "within_96h_before_window": "false",
        "within_7d_before_window": "false",
        "within_72h_after_window": "true",
        "within_96h_after_window": "true",
        "within_7d_after_window": "true",
        "home_domestic_matches_since_window_end_before_fixture": "0",
        "away_domestic_matches_since_window_end_before_fixture": "1",
        "home_first_domestic_league_match_after_window": "true",
        "away_first_domestic_league_match_after_window": "false",
        "both_first_domestic_league_match_after_window": "false",
        "either_first_domestic_league_match_after_window": "true",
        "player_level_international_status": "UNVERIFIED",
        "player_level_reason": "Calendar window only; player duty not evidenced",
        "final_tournaments_included": "false",
        "non_uefa_only_windows_included": "false",
        "calendar_reference_version": "PBK_STAGE80_UEFA_RELEVANT_FIFA_WINDOWS_2017_2025_V1",
        "calendar_source_count": "5",
        "calendar_level_only": "true",
        "as_known_calendar_reference": "true",
        "no_match_result_dependency": "true",
        "no_lookahead": "true",
        "provider_calls": "0",
        "historical_backfill_only": "true",
        "research_only": "true",
        "operational_betting_authority": "false",
        "creates_signal": "false",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }


class PBK14InternationalWindowMarketJoinTests(unittest.TestCase):
    def test_auto_high_join_is_exact_calendar_only_and_no_lookahead(self):
        rows, diag = j.project([market()], [bridge()], [context()])
        self.assertEqual(diag["joined_rows"], 1)
        self.assertEqual(diag["missing_market_rows"], 0)
        self.assertEqual(diag["missing_context_rows"], 0)
        self.assertEqual(diag["context_invalid_rows"], 0)
        row = rows[0]
        self.assertEqual(row["historical_match_id"], "m1")
        self.assertEqual(row["api_fixture_id"], "100")
        self.assertEqual(row["mapping_status"], "AUTO")
        self.assertEqual(row["nearest_window_id"], "2024_SEP")
        self.assertEqual(row["window_relation"], "AFTER")
        self.assertEqual(row["window_reference_contract"], "NEAREST_WINDOW_RELATION_GATED_V2")
        self.assertEqual(row["within_72h_after_window"], "true")
        self.assertEqual(row["home_first_domestic_league_match_after_window"], "true")
        self.assertEqual(row["player_level_international_status"], "UNVERIFIED")
        self.assertEqual(row["calendar_level_only"], "true")
        self.assertEqual(row["no_match_result_dependency"], "true")
        self.assertEqual(row["no_lookahead"], "true")
        self.assertEqual(row["fuzzy_string_matching_used"], "false")
        self.assertEqual(row["operational_betting_authority"], "false")


    def test_v1_context_without_reference_contract_is_fail_closed(self):
        c = context()
        c.pop("window_reference_contract")
        rows, diag = j.project([market()], [bridge()], [c])
        self.assertEqual(rows, [])
        self.assertEqual(diag["context_valid_rows"], 0)
        self.assertEqual(diag["context_invalid_rows"], 1)

    def test_review_and_unmapped_never_enter_join(self):
        rows, diag = j.project(
            [market("m1"), market("m2")],
            [bridge("m1", "100", "REVIEW"), bridge("m2", "101", "UNMAPPED")],
            [context("100"), context("101")],
        )
        self.assertEqual(rows, [])
        self.assertEqual(diag["bridge_eligible_rows"], 0)

    def test_missing_context_is_explicit_not_synthetic_zero(self):
        rows, diag = j.project([market()], [bridge()], [])
        self.assertEqual(rows, [])
        self.assertEqual(diag["missing_context_rows"], 1)
        self.assertEqual(diag["missing_market_rows"], 0)

    def test_player_level_confirmation_without_direct_evidence_is_fail_closed(self):
        c = context()
        c["player_level_international_status"] = "CONFIRMED"
        rows, diag = j.project([market()], [bridge()], [c])
        self.assertEqual(rows, [])
        self.assertEqual(diag["context_valid_rows"], 0)
        self.assertEqual(diag["context_invalid_rows"], 1)
        self.assertEqual(diag["missing_context_rows"], 1)

    def test_context_authority_leak_is_fail_closed(self):
        c = context()
        c["operational_betting_authority"] = "true"
        rows, diag = j.project([market()], [bridge()], [c])
        self.assertEqual(rows, [])
        self.assertEqual(diag["context_invalid_rows"], 1)

    def test_duplicate_provider_fixture_identity_is_detected(self):
        rows, diag = j.project(
            [market("m1"), market("m2")],
            [bridge("m1", "100", "AUTO"), bridge("m2", "100", "HIGH")],
            [context("100")],
        )
        self.assertEqual(diag["bridge_eligible_duplicate_api_fixture_ids"], 1)
        self.assertEqual(len(rows), 2)

    def test_duplicate_context_fixture_identity_is_detected(self):
        rows, diag = j.project(
            [market()],
            [bridge()],
            [context(), context()],
        )
        self.assertEqual(diag["context_duplicate_fixture_ids"], 1)
        self.assertEqual(len(rows), 1)

    def test_meta_reports_market_and_calendar_coverage_without_authority(self):
        rows, diag = j.project([market()], [bridge()], [context()])
        meta = j.build_meta(rows, diag)
        self.assertEqual(meta["closing_1x2_matches"], 1)
        self.assertEqual(meta["closing_total25_matches"], 1)
        self.assertEqual(meta["within_72h_after_rows"], 1)
        self.assertEqual(meta["either_first_domestic_after_window_rows"], 1)
        self.assertEqual(meta["window_reference_contract"], "NEAREST_WINDOW_RELATION_GATED_V2")
        self.assertEqual(meta["player_level_international_status"], "UNVERIFIED")
        self.assertFalse(meta["player_callup_inferred"])
        self.assertFalse(meta["player_travel_inferred"])
        self.assertFalse(meta["player_appearance_inferred"])
        self.assertEqual(meta["join_coverage_pct"], 100.0)
        self.assertTrue(meta["review_unmapped_excluded"])
        self.assertFalse(meta["fuzzy_string_matching_used"])
        self.assertTrue(meta["calendar_level_only"])
        self.assertTrue(meta["no_match_result_dependency"])
        self.assertTrue(meta["no_lookahead"])
        self.assertFalse(meta["operational_betting_authority"])
        self.assertFalse(meta["creates_signal"])


if __name__ == "__main__":
    unittest.main()
