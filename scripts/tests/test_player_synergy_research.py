import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.player_synergy_research as p


def xi(ids, positions=None):
    positions=positions or ["G","D","D","D","D","M","M","M","F","F","F"]
    return json.dumps([{"player":{"id":pid,"name":f"P{pid}","pos":positions[i]}} for i,pid in enumerate(ids)])


class PlayerSynergyResearchTests(unittest.TestCase):
    def test_parse_xi_requires_complete_unique_eleven(self):
        self.assertEqual(len(p.parse_xi(xi([str(i) for i in range(11)]))),11)
        self.assertEqual(p.parse_xi(xi(["1"]*11)),[])

    def test_fixture_outcomes_uses_canonical_pbk16_schema(self):
        out=p.fixture_outcomes([{"fixture_id":"1","status":"FT","home_goals":"2","away_goals":"1"}])
        self.assertEqual(out["1"]["home_points"],3)
        self.assertEqual(out["1"]["away_gd"],-1)

    def test_walk_forward_excludes_target_outcome_from_current_features(self):
        ids=[str(i) for i in range(1,12)]
        lineups=[]; fixtures=[]
        for n in range(1,7):
            lineups.append({"fixture_id":str(n),"team_id":"T","team_name":"Team","side":"HOME",
                            "kickoff_utc":f"2026-01-0{n}T12:00:00+00:00","formation":"4-3-3",
                            "starting_xi_json":xi(ids)})
            fixtures.append({"fixture_id":str(n),"status":"FT","home_goals":"1" if n<6 else "9","away_goals":"0"})
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            def write(path,fields,rows):
                with path.open("w",encoding="utf-8",newline="") as f:
                    import csv
                    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
            write(root/"historical_lineup_snapshots.csv",list(lineups[0]),lineups)
            write(root/"pbk16_all_competition_fixture_history.csv",list(fixtures[0]),fixtures)
            with patch.object(p,"LINEUPS",root/"historical_lineup_snapshots.csv"), patch.object(p,"FIXTURES",root/"pbk16_all_competition_fixture_history.csv"):
                pairs,trios,lines,anti,wf=p.build()
        target=[r for r in wf if r["fixture_id"]=="6"][0]
        self.assertGreater(target["pair_eligible_prior"],0)
        self.assertEqual(target["pair_prior_sample_mean"],5.0)
        self.assertEqual(target["strictly_prior_combo_history_only"],"YES")

    def test_negative_pair_can_be_flagged_only_with_sample(self):
        key=("PAIR","",("1","2"))
        combo={key:[(0.0,-1.0)]*5}
        players={"1":[(3.0,1.0)]*5,"2":[(3.0,1.0)]*5}
        row=p.association_from_history("T",key,{"1":"A","2":"B"},combo,players)
        self.assertEqual(row["eligible"],"true")
        self.assertEqual(row["association_direction"],"NEGATIVE")
        self.assertEqual(row["anti_synergy_candidate"],"true")
        self.assertEqual(row["causal_claim"],"false")

    def test_line_groups_are_position_specific(self):
        parsed=p.parse_xi(xi([str(i) for i in range(1,12)]))
        groups={g:len(players) for g,players in p.line_combos(parsed)}
        self.assertEqual(groups,{"D":4,"F":3,"M":3})


if __name__=="__main__":
    unittest.main()
