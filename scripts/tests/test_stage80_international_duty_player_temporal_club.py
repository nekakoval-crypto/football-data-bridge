import unittest
from scripts import stage80_international_duty_player_temporal_club as t

def ev(date="2024-09-05T18:00:00Z", pid="11"):
    return {"fixture_id":"500","kickoff_utc":date,"window_id":"2024_SEP","national_team_id":"1","national_team_name":"A","player_id":pid,"player_name":"P"}

def ident(pid="11", tm="900"):
    return {"player_id":pid,"transfermarkt_player_id":tm,"transfermarkt_identity_status":"SAFE_AUTO_HIGH"}

def tr(date, frm, to, eid, pid="11", tm="900"):
    return {"pbk_player_id":pid,"transfermarkt_player_id":tm,"transfer_date":date,"from_club_id":frm,"from_club_name":"F"+frm,"to_club_id":to,"to_club_name":"C"+to,"transfer_event_id":eid}

class TemporalClubTests(unittest.TestCase):
    def test_bounded_continuous_interval(self):
        rows,invalid=t.build([ev()], [ident()], [
            tr("2024-07-01","100","200","a"),
            tr("2025-01-01","200","300","b"),
        ])
        self.assertEqual(invalid,0)
        r=rows[0]
        self.assertEqual(r["temporal_club_status"],"BOUNDED_CHAIN_CONFIRMED")
        self.assertEqual(r["transfermarkt_club_id"],"200")
        self.assertEqual(r["chain_match_method"],"TRANSFERMARKT_CLUB_ID")
        self.assertEqual(r["current_club_substituted"],"false")

    def test_unbounded_after_last_event_is_not_inferred(self):
        rows,_=t.build([ev("2025-09-05T18:00:00Z")],[ident()],[tr("2024-07-01","100","200","a")])
        self.assertEqual(rows[0]["temporal_club_status"],"UNBOUNDED_INTERVAL")
        self.assertEqual(rows[0]["transfermarkt_club_id"],"")

    def test_unbounded_before_first_event_is_not_inferred(self):
        rows,_=t.build([ev("2023-09-05T18:00:00Z")],[ident()],[tr("2024-07-01","100","200","a")])
        self.assertEqual(rows[0]["temporal_club_status"],"UNBOUNDED_INTERVAL")

    def test_chain_break_is_not_inferred(self):
        rows,_=t.build([ev()],[ident()],[
            tr("2024-07-01","100","200","a"),
            tr("2025-01-01","999","300","b"),
        ])
        self.assertEqual(rows[0]["temporal_club_status"],"CHAIN_BREAK")
        self.assertEqual(rows[0]["transfermarkt_club_name"],"")

    def test_transfer_date_collision_is_ambiguous(self):
        rows,_=t.build([ev("2024-07-01T18:00:00Z")],[ident()],[
            tr("2024-07-01","100","200","a"),
            tr("2025-01-01","200","300","b"),
        ])
        self.assertEqual(rows[0]["temporal_club_status"],"TRANSFER_DATE_COLLISION")
        self.assertEqual(rows[0]["transfer_date_collision"],"true")

    def test_no_safe_identity(self):
        bad=ident(); bad["transfermarkt_identity_status"]="UNMAPPED"
        rows,_=t.build([ev()],[bad],[])
        self.assertEqual(rows[0]["temporal_club_status"],"NO_SAFE_TRANSFER_IDENTITY")

    def test_exact_name_fallback_when_ids_absent(self):
        a=tr("2024-07-01","","","a"); a["to_club_name"]="Same Club"
        b=tr("2025-01-01","","","b"); b["from_club_name"]="Same Club"; b["to_club_name"]="Next"
        rows,_=t.build([ev()],[ident()],[a,b])
        self.assertEqual(rows[0]["temporal_club_status"],"BOUNDED_CHAIN_CONFIRMED")
        self.assertEqual(rows[0]["chain_match_method"],"EXACT_CLUB_NAME")
        self.assertEqual(rows[0]["transfermarkt_club_name"],"Same Club")

if __name__=="__main__": unittest.main()
