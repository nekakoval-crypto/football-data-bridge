import json
import unittest
import scripts.player_synergy_forward_gate as p

def xi():
    positions=["G","D","D","D","D","M","M","M","F","F","F"]
    return json.dumps([{"id":str(i+1),"name":str(i+1),"pos":positions[i]} for i in range(11)])

class PlayerSynergyForwardGateTests(unittest.TestCase):
    def test_latest_prematch_rejects_postkickoff(self):
        rows=[{"fixture_id":"1","team_id":"T","official_lineup":"YES",
               "captured_at_utc":"2026-01-01T12:01:00Z","kickoff_utc":"2026-01-01T12:00:00Z",
               "starting_xi_json":xi()}]
        self.assertEqual(p.latest_prematch_official(rows),[])

    def test_latest_prematch_keeps_latest_valid_observation(self):
        rows=[]
        for t in ("11:40:00","11:50:00"):
            rows.append({"fixture_id":"1","team_id":"T","team_name":"A","side":"HOME","formation":"4-3-3",
                         "official_lineup":"YES","captured_at_utc":f"2026-01-01T{t}Z",
                         "kickoff_utc":"2026-01-01T12:00:00Z","starting_xi_json":xi()})
        out=p.latest_prematch_official(rows)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["captured"].minute,50)

    def test_pair_summary_is_separate_and_weighted(self):
        research=[{"team_id":"T","member_ids":"1|2","position_group":"","eligible":"true",
                   "association_direction":"POSITIVE","anti_synergy_candidate":"false",
                   "points_delta_vs_member_baseline":"0.4","co_starts":"10"}]
        idx=p.research_index(research)
        parsed=p.parse_xi(xi())
        s=p.summarize_dimension("T",parsed,"PAIR",idx)
        self.assertEqual(s["pair_research_eligible"],1)
        self.assertEqual(s["pair_positive"],1)
        self.assertAlmostEqual(s["pair_weighted_delta_mean"],0.4)

    def test_no_probability_authority_in_forward_rows(self):
        lineup=[{"fixture_id":"1","team_id":"T","team_name":"A","side":"HOME","formation":"4-3-3",
                 "official_lineup":"YES","captured_at_utc":"2026-01-01T11:50:00Z",
                 "kickoff_utc":"2026-01-01T12:00:00Z","starting_xi_json":xi()}]
        out=p.build_forward(lineup,[],[],[])
        self.assertEqual(out[0]["prematch_observation_authority"],"PREMATCH_FROZEN")
        self.assertEqual(out[0]["probability_authority"],"NOT_AUTHORIZED")
        self.assertEqual(out[0]["creates_signal"],"false")

if __name__=="__main__":
    unittest.main()
