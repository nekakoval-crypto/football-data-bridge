import unittest
from scripts import stage80_international_duty_return_load as r


def ev(fid="100", kickoff="2025-11-18T19:45:00Z", pid="10", window="2025_NOV",
       appearance="true", minutes="90"):
    return {
        "fixture_id":fid,"kickoff_utc":kickoff,"window_id":window,
        "national_team_id":"1","national_team_name":"Nation",
        "player_id":pid,"player_name":"Player",
        "appearance_confirmed":appearance,
        "minutes_confirmed":"true" if minutes != "" else "false",
        "minutes":minutes,
    }


def club(fid="100", pid="10", team="50"):
    return {
        "fixture_id":fid,"player_id":pid,
        "pbk16_club_identity_status":"PBK16_EXACT_ALIAS_UNIQUE",
        "pbk16_team_id":team,"pbk16_team_name":"Club",
        "pbk16_provider_league_id":"39",
    }


def domestic(fid, kickoff, home="50", away="60", status="FT"):
    return {
        "fixture_id":fid,"competition_role":"DOMESTIC_LEAGUE",
        "kickoff_utc":kickoff,"status":status,
        "home_team_id":home,"home_team":"Club",
        "away_team_id":away,"away_team":"Opp",
    }


class ReturnLoadTests(unittest.TestCase):
    def test_direct_minutes_and_next_played_domestic_return(self):
        rows,audit=r.build(
            [ev("99","2025-11-15T19:45:00Z",minutes="30"),
             ev("100","2025-11-18T19:45:00Z",minutes="90")],
            [club()],
            [domestic("200","2025-11-22T15:00:00Z")],
        )
        self.assertEqual(audit["mapped_rows_missing_direct_evidence"],0)
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row["window_confirmed_appearances_through_event"],"2")
        self.assertEqual(row["window_confirmed_minutes_through_event"],"120")
        self.assertEqual(row["confirmed_minutes"],"90")
        self.assertEqual(row["next_domestic_fixture_id"],"200")
        self.assertEqual(row["club_side"],"HOME")
        self.assertEqual(row["formal_callup_inferred"],"false")
        self.assertEqual(row["travel_inferred"],"false")

    def test_nonappearance_does_not_add_appearance_or_minutes(self):
        rows,_=r.build(
            [ev("100",appearance="false",minutes="")],
            [club()],
            [domestic("200","2025-11-22T15:00:00Z")],
        )
        self.assertEqual(rows[0]["window_confirmed_appearances_through_event"],"0")
        self.assertEqual(rows[0]["window_confirmed_minutes_through_event"],"0")
        self.assertEqual(rows[0]["confirmed_minutes"],"")

    def test_skips_unmapped_club_identity(self):
        c=club()
        c["pbk16_club_identity_status"]="OUTSIDE_PBK16_OR_UNMAPPED"
        rows,_=r.build([ev()],[c],[domestic("200","2025-11-22T15:00:00Z")])
        self.assertEqual(rows,[])

    def test_skips_cancelled_return_and_uses_next_played_fixture(self):
        rows,_=r.build(
            [ev()],[club()],
            [
                domestic("199","2025-11-20T15:00:00Z",status="PST"),
                domestic("200","2025-11-22T15:00:00Z",status="FT"),
            ],
        )
        self.assertEqual(rows[0]["next_domestic_fixture_id"],"200")
        self.assertEqual(rows[0]["return_fixture_played_only"],"true")

    def test_away_side_and_opponent_are_derived_exactly(self):
        rows,_=r.build(
            [ev()],[club(team="50")],
            [domestic("200","2025-11-22T15:00:00Z",home="60",away="50")],
        )
        self.assertEqual(rows[0]["club_side"],"AWAY")
        self.assertEqual(rows[0]["opponent_team_id"],"60")

    def test_no_later_played_domestic_fixture_fails_closed(self):
        rows,audit=r.build(
            [ev()],[club()],
            [domestic("150","2025-11-10T15:00:00Z")],
        )
        self.assertEqual(rows,[])
        self.assertEqual(audit["mapped_rows_without_later_played_domestic_fixture"],1)

    def test_return_thresholds(self):
        rows,_=r.build(
            [ev(kickoff="2025-11-18T12:00:00Z")],[club()],
            [domestic("200","2025-11-21T11:00:00Z")],
        )
        self.assertEqual(rows[0]["return_within_72h"],"true")
        self.assertEqual(rows[0]["return_within_96h"],"true")
        self.assertEqual(rows[0]["return_within_7d"],"true")


if __name__=="__main__":
    unittest.main()
