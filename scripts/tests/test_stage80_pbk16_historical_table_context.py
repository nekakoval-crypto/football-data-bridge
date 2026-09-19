import unittest

from scripts import stage80_pbk16_historical_table_context as t


def fixture(fid,day,home,away,hg,ag,status="FT"):
    return {
        "fixture_id":str(fid),
        "competition_role":"DOMESTIC_LEAGUE",
        "country":"Testland",
        "provider_competition_id":"999",
        "competition_name":"Test League",
        "season":"2024",
        "round":"Regular Season - 1",
        "kickoff_utc":f"{day}T15:00:00Z",
        "status":status,
        "home_team_id":str(home),"home_team":f"T{home}",
        "away_team_id":str(away),"away_team":f"T{away}",
        "home_goals":str(hg),"away_goals":str(ag),
    }


def audit(fid,role="TABLE_PHASE",family="REGULAR",policy="PLAYED_RESULT_USABLE",requires=False):
    return {
        "fixture_id":str(fid),
        "phase_role":role,
        "phase_family":family,
        "table_result_policy":policy,
        "season_format_contract_required":"true" if requires else "false",
    }


class PBK16HistoricalTableContextTests(unittest.TestCase):
    def test_same_day_results_are_excluded(self):
        rows=[
            fixture(1,"2024-08-01",1,2,1,0),
            fixture(2,"2024-08-01",3,4,2,2),
            fixture(3,"2024-08-02",1,3,0,1),
            fixture(4,"2024-08-02",2,4,1,1),
        ]
        audits=[audit(i) for i in range(1,5)]
        out,diag=t.project(rows,audits)
        by={r["domestic_fixture_id"]:r for r in out}
        self.assertEqual(diag["invalid_played_result_rows"],0)
        self.assertEqual(by["1"]["home_points_pre"],0)
        self.assertEqual(by["2"]["home_points_pre"],0)
        self.assertEqual(by["3"]["home_points_pre"],3)
        self.assertEqual(by["3"]["away_points_pre"],1)
        self.assertEqual(by["3"]["same_day_results_excluded"],"true")
        self.assertEqual(by["3"]["no_lookahead"],"true")

    def test_split_table_phase_is_blocked_and_taints_later_table_state(self):
        rows=[
            fixture(1,"2024-08-01",1,2,1,0),
            fixture(2,"2024-08-02",1,2,2,0),
            fixture(3,"2024-08-03",1,2,0,1),
        ]
        audits=[
            audit(1),
            audit(2,family="CHAMPIONSHIP_SPLIT",requires=True),
            audit(3),
        ]
        out,_=t.project(rows,audits)
        by={r["domestic_fixture_id"]:r for r in out}
        self.assertEqual(
            by["2"]["context_status"],
            "BLOCKED_TABLE_PHASE_REQUIRES_SEASON_FORMAT_CONTRACT",
        )
        self.assertEqual(by["2"]["home_points_pre"],"")
        self.assertEqual(
            by["3"]["context_status"],
            "BLOCKED_AFTER_UNMODELED_TABLE_PHASE",
        )
        self.assertEqual(by["3"]["home_rank_pre"],"")

    def test_post_table_playoff_is_excluded_without_appendix_team_pollution(self):
        rows=[
            fixture(1,"2024-08-01",1,2,1,0),
            fixture(2,"2024-08-02",1,99,0,0),
        ]
        audits=[
            audit(1),
            audit(
                2,role="POST_TABLE_PLAYOFF",family="RELEGATION_PLAYOFF",
                policy="NOT_FOR_LEAGUE_TABLE_RECONSTRUCTION",
            ),
        ]
        out,_=t.project(rows,audits)
        by={r["domestic_fixture_id"]:r for r in out}
        self.assertEqual(by["1"]["core_participant_teams"],2)
        self.assertEqual(by["2"]["core_participant_teams"],2)
        self.assertEqual(
            by["2"]["context_status"],
            "POST_TABLE_PLAYOFF_EXCLUDED_FROM_TABLE",
        )
        self.assertEqual(by["2"]["home_points_pre"],"")

    def test_awarded_result_taints_subsequent_regular_context(self):
        rows=[
            fixture(1,"2024-08-01",1,2,1,0),
            fixture(2,"2024-08-02",1,2,0,0,status="AWD"),
            fixture(3,"2024-08-03",1,2,0,1),
        ]
        audits=[
            audit(1),
            audit(2,policy="AWARDED_RESULT_REQUIRES_RULE_EVIDENCE"),
            audit(3),
        ]
        out,_=t.project(rows,audits)
        by={r["domestic_fixture_id"]:r for r in out}
        self.assertEqual(
            by["2"]["context_status"],
            "VALID_PREMATCH_AWARDED_RESULT_WILL_TAINT",
        )
        self.assertEqual(by["2"]["home_points_pre"],3)
        self.assertEqual(
            by["3"]["context_status"],
            "BLOCKED_PRIOR_AWARDED_RESULT_UNRESOLVED",
        )
        self.assertEqual(by["3"]["home_points_pre"],"")

    def test_cancelled_fixture_does_not_taint_state(self):
        rows=[
            fixture(1,"2024-08-01",1,2,1,0),
            fixture(2,"2024-08-02",1,2,0,0,status="CANC"),
            fixture(3,"2024-08-03",1,2,0,1),
        ]
        audits=[
            audit(1),
            audit(2,policy="NOT_PLAYED_EXCLUDE"),
            audit(3),
        ]
        out,_=t.project(rows,audits)
        by={r["domestic_fixture_id"]:r for r in out}
        self.assertEqual(
            by["2"]["context_status"],
            "VALID_PREMATCH_NOT_PLAYED_NO_STATE_MUTATION",
        )
        self.assertEqual(by["3"]["context_status"],"VALID_REGULAR_RESULTS_DERIVED")
        self.assertEqual(by["3"]["home_points_pre"],3)

    def test_missing_phase_audit_fails_closed(self):
        rows=[fixture(1,"2024-08-01",1,2,1,0)]
        out,diag=t.project(rows,[])
        self.assertEqual(diag["source_without_phase_audit"],1)
        self.assertEqual(out[0]["context_status"],"BLOCKED_MISSING_PHASE_AUDIT")
        self.assertEqual(out[0]["home_points_pre"],"")

    def test_regular_context_never_claims_official_or_motivation_authority(self):
        rows=[fixture(1,"2024-08-01",1,2,1,0)]
        out,_=t.project(rows,[audit(1)])
        row=out[0]
        self.assertEqual(row["context_status"],"VALID_REGULAR_RESULTS_DERIVED")
        self.assertEqual(row["official_table_equivalence"],"false")
        self.assertEqual(row["exact_title_relegation_motivation_allowed"],"false")
        self.assertEqual(row["europe_status"],"UNKNOWN_BY_DESIGN")
        self.assertEqual(row["operational_betting_authority"],"false")
        self.assertEqual(row["creates_signal"],"false")

    def test_rank_contract_is_points_gd_gf_then_team(self):
        states={
            "A":{"played":2,"points":4,"gf":3,"ga":1},
            "B":{"played":2,"points":4,"gf":2,"ga":0},
            "C":{"played":2,"points":3,"gf":5,"ga":1},
        }
        table=t.ranked(states)
        self.assertEqual([r["team"] for r in table],["A","B","C"])
        self.assertEqual([r["rank"] for r in table],[1,2,3])


if __name__=="__main__":
    unittest.main()
