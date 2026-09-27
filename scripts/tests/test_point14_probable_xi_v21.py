import json
import unittest
from scripts.point14_probable_xi_v21 import probable_xi_for_team


def tenure():
    return {
        "team_id":"33","team_name":"Team","coach_name":"Coach",
        "valid_from_utc":"2026-01-13","valid_to_utc":"",
        "effective_precision":"DATE","temporal_authority":"HISTORICAL_VERIFIED"
    }


def xi(ids):
    rows=[]
    for i,pid in enumerate(ids):
        if i == 0: grid="1:1"; pos="G"
        elif i < 5: grid=f"2:{5-i}"; pos="D"
        elif i < 7: grid=f"3:{7-i}"; pos="M"
        elif i < 10: grid=f"4:{10-i}"; pos="M"
        else: grid="5:1"; pos="F"
        rows.append({"id":str(pid),"name":f"P{pid}","grid":grid,"pos":pos})
    return json.dumps(rows)


def row(fid, day, ids, formation="4-2-3-1"):
    return {
        "team_id":"33","fixture_id":str(fid),
        "kickoff_utc":f"2026-02-{day:02d}T20:00:00+00:00",
        "formation":formation,"starting_xi_count":"11",
        "starting_xi_json":xi(ids),
        "retrieved_at_utc":"2026-09-27T00:00:00Z"
    }


class TestProbableXiV21(unittest.TestCase):
    def test_returns_11_for_stable_formation(self):
        rows=[row(i,i+1,list(range(1,12))) for i in range(1,6)]
        r=probable_xi_for_team(tenure(),rows)
        self.assertEqual(r["status"],"EXPECTED_XI_READY_UNCALIBRATED")
        self.assertEqual(len(r["expected_xi"]),11)
        self.assertEqual(r["base_formation"],"4-2-3-1")

    def test_recent_slot_breaks_equal_start_tie(self):
        base=list(range(1,12))
        alt=base.copy(); alt[10]=12
        rows=[
            row(1,1,base),
            row(2,2,base),
            row(3,3,alt),
            row(4,4,alt),
        ]
        r=probable_xi_for_team(tenure(),rows)
        striker=next(p for p in r["expected_xi"] if p["grid"]=="5:1")
        self.assertEqual(striker["player_id"],"12")

    def test_probabilities_are_not_claimed(self):
        rows=[row(i,i+1,list(range(1,12))) for i in range(1,6)]
        r=probable_xi_for_team(tenure(),rows)
        self.assertEqual(r["probability_status"],"UNCALIBRATED")
        self.assertFalse(r["operational_betting_authority"])


if __name__=="__main__":
    unittest.main()
