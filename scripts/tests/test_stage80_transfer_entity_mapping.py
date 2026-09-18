import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_transfer_entity_mapping import build_mapping, build_transfer_history, run


class Stage80TransferEntityMappingTests(unittest.TestCase):
    def test_exact_name_and_current_club_is_only_auto_policy(self):
        pbk=[{
            "player_id":"1","latest_observed_name":"Harry Kane",
            "latest_roster_team_names":"Bayern München",
        }]
        tm=[{
            "player_id":"100","name":"Harry Kane","current_club_id":"10",
            "current_club_name":"Bayern Munich",
        }]
        rows,auto=build_mapping(pbk,tm)
        self.assertEqual(rows[0]["match_status"],"AUTO_MATCH")
        self.assertEqual(rows[0]["match_method"],"EXACT_NAME_CURRENT_CLUB")
        self.assertIn("100",auto)

    def test_initial_surname_team_is_review_only(self):
        pbk=[{
            "player_id":"1","latest_observed_name":"H. Kane",
            "latest_roster_team_names":"Bayern München",
        }]
        tm=[{
            "player_id":"100","name":"Harry Kane","current_club_id":"10",
            "current_club_name":"Bayern Munich",
        }]
        rows,auto=build_mapping(pbk,tm)
        self.assertEqual(rows[0]["match_status"],"REVIEW")
        self.assertEqual(rows[0]["match_method"],"INITIAL_SURNAME_CURRENT_CLUB")
        self.assertEqual(auto,{})

    def test_ambiguous_exact_name_never_auto_maps(self):
        pbk=[{"player_id":"1","latest_observed_name":"John Smith","latest_roster_team_names":""}]
        tm=[
            {"player_id":"100","name":"John Smith","current_club_name":"Alpha"},
            {"player_id":"101","name":"John Smith","current_club_name":"Beta"},
        ]
        rows,auto=build_mapping(pbk,tm)
        self.assertTrue(all(r["match_status"]=="REVIEW" for r in rows))
        self.assertEqual(auto,{})

    def test_transfer_history_uses_auto_mapping_only(self):
        transfers=[
            {"player_id":"100","player_name":"Harry Kane","transfer_date":"2023-08-12",
             "transfer_season":"23/24","from_club_id":"20","from_club_name":"Tottenham",
             "to_club_id":"10","to_club_name":"Bayern Munich","transfer_fee":"95000000",
             "market_value_in_eur":"90000000"},
            {"player_id":"101","player_name":"Other","transfer_date":"2023-01-01"},
        ]
        history=build_transfer_history(transfers,{"100":{"pbk_player_id":"1","method":"EXACT_NAME_CURRENT_CLUB","confidence":"HIGH"}})
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]["pbk_player_id"],"1")

    def test_end_to_end_supports_gzip(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            pbk=root/"historical_players.csv"
            with pbk.open("w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["player_id","latest_observed_name","latest_roster_team_names"])
                w.writeheader(); w.writerow({"player_id":"1","latest_observed_name":"Harry Kane","latest_roster_team_names":"Bayern München"})
            players=root/"players.csv.gz"
            with gzip.open(players,"wt",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["player_id","name","current_club_id","current_club_name"])
                w.writeheader(); w.writerow({"player_id":"100","name":"Harry Kane","current_club_id":"10","current_club_name":"Bayern Munich"})
            transfers=root/"transfers.csv.gz"
            with gzip.open(transfers,"wt",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["player_id","player_name","transfer_date","transfer_season","from_club_id","from_club_name","to_club_id","to_club_name","transfer_fee","market_value_in_eur"])
                w.writeheader(); w.writerow({"player_id":"100","player_name":"Harry Kane","transfer_date":"2023-08-12","transfer_season":"23/24","from_club_id":"20","from_club_name":"Tottenham","to_club_id":"10","to_club_name":"Bayern Munich","transfer_fee":"95000000","market_value_in_eur":"90000000"})
            meta=run(pbk,players,transfers,root/"mapping.csv",root/"history.csv",root/"meta.json")
            self.assertEqual(meta["auto_mapped_players"],1)
            self.assertEqual(meta["normalized_transfer_rows"],1)
            self.assertTrue((root/"mapping.csv").exists())


if __name__=="__main__":
    unittest.main()
