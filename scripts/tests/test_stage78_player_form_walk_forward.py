import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import stage78_player_form_walk_forward as m

class T(unittest.TestCase):
    def fx(self,fid,k,season="2025"):return {"fixture_id":str(fid),"country":"Norway","competition_name":"Eliteserien","season":season,"kickoff_utc":k,"home_team_id":"10","home_team":"A","away_team_id":"20","away_team":"B","home_goals":"2","away_goals":"1"}
    def g(self,fid,k,grade,obs=None):return {"fixture_id":str(fid),"team_id":"10","player_id":"7","player_name":"P","position_group":"M","kickoff_utc":k,"observed_at_utc":obs or k,"overall_grade":str(grade)}
    def test_windows_prior_only(self):
        f=[self.fx(i,f"2025-0{i}-01T12:00:00Z") for i in range(1,7)];g=[self.g(i,f"2025-0{i}-01T12:00:00Z",i) for i in range(1,7)]
        rows,meta=m.build(g,f);r=rows[-1]
        self.assertEqual((r["sample_3"],r["form_3"]),(3,4.0));self.assertEqual((r["sample_5"],r["form_5"]),(5,3.0));self.assertEqual(r["team_points"],3);self.assertEqual(meta["leakage_violations"],0)
    def test_future_observation_excluded(self):
        f=[self.fx("1","2025-01-01T12:00:00Z"),self.fx("2","2025-02-01T12:00:00Z")]
        g=[self.g("1","2025-01-01T12:00:00Z",9,"2025-03-01T00:00:00Z"),self.g("2","2025-02-01T12:00:00Z",5)]
        rows,_=m.build(g,f);r=[x for x in rows if x["fixture_id"]=="2"][0];self.assertEqual(r["season_sample"],0);self.assertIsNone(r["last_grade"])
    def test_season_reset(self):
        f=[self.fx("1","2024-01-01T12:00:00Z","2024"),self.fx("2","2025-01-01T12:00:00Z","2025")]
        g=[self.g("1","2024-01-01T12:00:00Z",8),self.g("2","2025-01-01T12:00:00Z",6)]
        rows,_=m.build(g,f);r=[x for x in rows if x["fixture_id"]=="2"][0];self.assertEqual(r["season_sample"],0)
if __name__=="__main__":unittest.main()
