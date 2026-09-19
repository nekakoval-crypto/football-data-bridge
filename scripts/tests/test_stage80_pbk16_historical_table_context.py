import unittest

from scripts import stage80_pbk16_historical_table_context as t


def fixture(fid,day,home,away,hg,ag,round_name="Regular Season - 1",status="FT"):
    return {
        "fixture_id":str(fid),
        "competition_role":"DOMESTIC_LEAGUE",
        "country":"Testland",
        "provider_competition_id":"999",
        "competition_name":"Test League",
        "season":"2024",
        "round":round_name,
        "kickoff_utc":f"{day}T15:00:00Z",
        "status":status,
        "home_team_id":str(home),"home_team":f"T{home}",
        "away_team_id":str(away),"away_team":f"T{away}",
        "home_goals":str(hg),"away_goals":str(ag),
    }


class PBK16HistoricalTableContextTests(unittest.TestCase):
    def test_nonregular_round_detection(self):
        self.assertTrue(t.is_nonregular_round("Championship Round - 1"))
        self.assertTrue(t.is_nonregular_round("Relegation Round"))
        self.assertTrue(t.is_nonregular_round("Conference League Play-offs - Final"))
        self.assertTrue(t.is_nonregular_round("Finals"))
        self.assertFalse(t.is_nonregular_round("Regular Season - 34"))

    def test_same_day_results_are_excluded(self):
        rows=[
            fixture(1,"2024-08-01",1,2,1,0),
            fixture(2,"2024-08-01",3,4,2,2),
            fixture(3,"2024-08-02",1,3,0,1),
            fixture(4,"2024-08-02",2,4,1,1),
        ]
        out,diag=t.project(rows)
        by={r["domestic_fixture_id"]:r for r in out}
        self.assertEqual(diag["invalid_regular_result_rows"],0)
        self.assertEqual(by["1"]["home_points_pre"],0)
        self.assertEqual(by["2"]["home_points_pre"],0)
        self.assertEqual(by["3"]["home_points_pre"],3)
        self.assertEqual(by["3"]["away_points_pre"],1)
        self.assertEqual(by["3"]["same_day_results_excluded"],"true")
        self.assertEqual(by["3"]["no_lookahead"],"true")

    def test_nonregular_phase_is_blocked_and_does_not_mutate_state(self):
        rows=[
            fixture(1,"2024-08-01",1,2,1,0),
            fixture(2,"2024-08-02",1,2,2,0,"Championship Round - 1"),
            fixture(3,"2024-08-03",1,2,0,1,"Regular Season - 2"),
        ]
        out,_=t.project(rows)
        by={r["domestic_fixture_id"]:r for r in out}
        self.assertEqual(by["2"]["phase_class"],"NONREGULAR_PHASE")
        self.assertEqual(by["2"]["context_status"],"BLOCKED_NONREGULAR_PHASE_UNMODELED")
        self.assertEqual(by["2"]["home_rank_pre"],"")
        # The blocked 2-0 result never updates V1 state.
        self.assertEqual(by["3"]["home_points_pre"],3)
        self.assertEqual(by["3"]["away_points_pre"],0)

    def test_appendix_team_is_not_part_of_core_universe(self):
        rows=[
            fixture(1,"2024-08-01",1,2,1,0),
            fixture(2,"2024-08-02",2,1,1,1),
            fixture(3,"2024-08-03",1,99,0,0,"Relegation Round"),
        ]
        out,_=t.project(rows)
        by={r["domestic_fixture_id"]:r for r in out}
        self.assertEqual(by["1"]["core_participant_teams"],2)
        self.assertEqual(by["3"]["core_participant_teams"],2)
        self.assertEqual(by["3"]["context_status"],"BLOCKED_NONREGULAR_PHASE_UNMODELED")

    def test_regular_context_never_claims_official_or_motivation_authority(self):
        rows=[fixture(1,"2024-08-01",1,2,1,0)]
        out,_=t.project(rows)
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
