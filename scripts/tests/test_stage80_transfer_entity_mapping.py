import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_transfer_entity_mapping import (
    AUTO_METHOD_STATS,
    build_identity_map,
    build_mapping,
    build_transfer_history,
    run,
)


class Stage80TransferEntityMappingTests(unittest.TestCase):
    def test_exact_name_and_current_club_is_only_catalog_auto_policy(self):
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

    def test_full_player_stats_name_and_same_club_can_auto_high(self):
        pbk=[{
            "player_id":"5","latest_observed_name":"M. Akanji",
            "latest_roster_team_names":"Inter",
        }]
        stats=[{
            "player_id":"5","player_name":"Manuel Akanji","team_name":"Inter",
        }]
        tm=[{
            "player_id":"100","name":"Manuel Akanji","current_club_id":"46",
            "current_club_name":"Inter",
        }]
        rows,auto=build_mapping(pbk,tm,stats)
        self.assertEqual(rows[0]["match_status"],"AUTO_MATCH")
        self.assertEqual(rows[0]["match_method"],AUTO_METHOD_STATS)
        self.assertEqual(rows[0]["match_confidence"],"HIGH")
        self.assertEqual(rows[0]["pbk_evidence_name"],"Manuel Akanji")
        self.assertEqual(rows[0]["pbk_evidence_team_name"],"Inter")
        self.assertIn("100",auto)

    def test_abbreviated_player_stats_name_never_creates_stats_auto(self):
        pbk=[{
            "player_id":"5","latest_observed_name":"M. Akanji",
            "latest_roster_team_names":"Inter",
        }]
        stats=[{
            "player_id":"5","player_name":"M. Akanji","team_name":"Inter",
        }]
        tm=[{
            "player_id":"100","name":"Manuel Akanji","current_club_id":"46",
            "current_club_name":"Inter",
        }]
        rows,auto=build_mapping(pbk,tm,stats)
        self.assertEqual(rows[0]["match_status"],"REVIEW")
        self.assertEqual(rows[0]["match_method"],"INITIAL_SURNAME_CURRENT_CLUB")
        self.assertEqual(auto,{})

    def test_stats_full_name_wrong_club_never_auto_maps(self):
        pbk=[{
            "player_id":"5","latest_observed_name":"M. Akanji",
            "latest_roster_team_names":"Inter",
        }]
        stats=[{
            "player_id":"5","player_name":"Manuel Akanji","team_name":"Inter",
        }]
        tm=[{
            "player_id":"100","name":"Manuel Akanji","current_club_id":"999",
            "current_club_name":"Other Club",
        }]
        rows,auto=build_mapping(pbk,tm,stats)
        self.assertNotEqual(rows[0]["match_status"],"AUTO_MATCH")
        self.assertEqual(auto,{})

    def test_stats_alias_shared_by_multiple_pbk_ids_never_auto_maps(self):
        pbk=[
            {"player_id":"1","latest_observed_name":"M. Akanji","latest_roster_team_names":"Inter"},
            {"player_id":"2","latest_observed_name":"M. Akanji","latest_roster_team_names":"Inter"},
        ]
        stats=[
            {"player_id":"1","player_name":"Manuel Akanji","team_name":"Inter"},
            {"player_id":"2","player_name":"Manuel Akanji","team_name":"Inter"},
        ]
        tm=[{
            "player_id":"100","name":"Manuel Akanji","current_club_id":"46",
            "current_club_name":"Inter",
        }]
        rows,auto=build_mapping(pbk,tm,stats)
        self.assertTrue(all(r["match_status"]!="AUTO_MATCH" for r in rows))
        self.assertEqual(auto,{})

    def test_transfermarkt_auto_claim_collision_is_demoted(self):
        pbk=[
            {"player_id":"1","latest_observed_name":"Harry Kane","latest_roster_team_names":"Bayern Munich"},
            {"player_id":"2","latest_observed_name":"Harry Kane","latest_roster_team_names":"Bayern Munich"},
        ]
        tm=[{
            "player_id":"100","name":"Harry Kane","current_club_id":"10",
            "current_club_name":"Bayern Munich",
        }]
        rows,auto=build_mapping(pbk,tm)
        self.assertTrue(all(r["match_status"]=="REVIEW" for r in rows))
        self.assertTrue(all(r["match_confidence"]=="LOW" for r in rows))
        self.assertEqual(auto,{})

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

    def test_identity_map_preserves_auto_high_even_without_transfer_rows(self):
        mapping_rows = [{
            "pbk_player_id": "5",
            "pbk_player_name": "M. Akanji",
            "transfermarkt_player_id": "100",
            "transfermarkt_player_name": "Manuel Akanji",
            "match_method": AUTO_METHOD_STATS,
            "match_status": "AUTO_MATCH",
            "match_confidence": "HIGH",
        }]
        identities = build_identity_map(mapping_rows)
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0]["pbk_player_id"], "5")
        self.assertEqual(identities[0]["transfermarkt_player_name"], "Manuel Akanji")
        self.assertEqual(identities[0]["mapping_method"], AUTO_METHOD_STATS)

    def test_review_mapping_never_enters_identity_map(self):
        mapping_rows = [{
            "pbk_player_id": "5",
            "pbk_player_name": "M. Akanji",
            "transfermarkt_player_id": "100",
            "transfermarkt_player_name": "Manuel Akanji",
            "match_method": "INITIAL_SURNAME_CURRENT_CLUB",
            "match_status": "REVIEW",
            "match_confidence": "MEDIUM",
        }]
        self.assertEqual(build_identity_map(mapping_rows), [])

    def test_transfer_history_uses_auto_mapping_only(self):
        transfers=[
            {"player_id":"100","player_name":"Harry Kane","transfer_date":"2023-08-12",
             "transfer_season":"23/24","from_club_id":"20","from_club_name":"Tottenham",
             "to_club_id":"10","to_club_name":"Bayern Munich","transfer_fee":"95000000",
             "market_value_in_eur":"90000000"},
            {"player_id":"101","player_name":"Other","transfer_date":"2023-01-01"},
        ]
        history=build_transfer_history(transfers,{"100":{
            "pbk_player_id":"1","method":AUTO_METHOD_STATS,"confidence":"HIGH"
        }})
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]["pbk_player_id"],"1")
        self.assertEqual(history[0]["mapping_method"],AUTO_METHOD_STATS)

    def test_end_to_end_supports_gzip_and_player_stats(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            pbk=root/"historical_players.csv"
            with pbk.open("w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["player_id","latest_observed_name","latest_roster_team_names"])
                w.writeheader()
                w.writerow({"player_id":"5","latest_observed_name":"M. Akanji","latest_roster_team_names":"Inter"})

            stats=root/"player_stats_snapshots.csv"
            with stats.open("w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["player_id","player_name","team_name"])
                w.writeheader()
                w.writerow({"player_id":"5","player_name":"Manuel Akanji","team_name":"Inter"})

            players=root/"players.csv.gz"
            with gzip.open(players,"wt",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["player_id","name","current_club_id","current_club_name"])
                w.writeheader()
                w.writerow({"player_id":"100","name":"Manuel Akanji","current_club_id":"46","current_club_name":"Inter"})

            transfers=root/"transfers.csv.gz"
            with gzip.open(transfers,"wt",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=[
                    "player_id","player_name","transfer_date","transfer_season",
                    "from_club_id","from_club_name","to_club_id","to_club_name",
                    "transfer_fee","market_value_in_eur",
                ])
                w.writeheader()
                w.writerow({
                    "player_id":"100","player_name":"Manuel Akanji",
                    "transfer_date":"2022-09-01","transfer_season":"22/23",
                    "from_club_id":"20","from_club_name":"Old",
                    "to_club_id":"46","to_club_name":"Inter",
                    "transfer_fee":"","market_value_in_eur":"",
                })

            meta=run(
                pbk,players,transfers,
                root/"mapping.csv",root/"history.csv",root/"meta.json",
                player_stats_path=stats,
                identity_out=root/"identity.csv",
            )
            self.assertEqual(meta["auto_mapped_players"],1)
            self.assertEqual(meta["verified_identity_rows"],1)
            self.assertEqual(meta["auto_mapped_by_method"][AUTO_METHOD_STATS],1)
            self.assertEqual(meta["normalized_transfer_rows"],1)
            self.assertTrue((root/"mapping.csv").exists())
            self.assertTrue((root/"identity.csv").exists())


if __name__=="__main__":
    unittest.main()
