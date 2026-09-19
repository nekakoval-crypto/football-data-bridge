import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_international_duty_player_identity_join as j


def evidence(player_id="1001", name="Player A", fixture="5001", minutes="90"):
    return {
        "fixture_id": fixture,
        "provider_league_id": "32",
        "competition_name": "World Cup - Qualification Europe",
        "candidate_family": "WORLD_CUP_QUALIFICATION",
        "season": "2024",
        "round": "Group Stage - 1",
        "kickoff_utc": "2025-09-05T18:45:00Z",
        "window_id": "2025_SEP",
        "national_team_id": "10",
        "national_team_name": "Country A",
        "player_id": player_id,
        "player_name": name,
        "position": "M",
        "number": "",
        "grid": "",
        "evidence_tier": "DIRECT_MINUTES",
        "capture_endpoint": "/fixtures/players",
        "evidence_source_type": "FIXTURE_PLAYER_STATS",
        "lineup_role": "APPEARANCE_ROLE_UNVERIFIED",
        "minutes": minutes,
        "provider_substitute_flag": "false",
        "provider_captain_flag": "false",
        "provider_rating": "7.0",
        "matchday_squad_confirmed": "true",
        "appearance_confirmed": "true" if int(minutes) > 0 else "false",
        "minutes_confirmed": "true",
        "starter_listed_confirmed": "false",
        "substitute_listed_confirmed": "false",
        "substitute_appearance_confirmed": "false",
        "formal_callup_status": "NOT_SEPARATELY_VERIFIED",
        "travel_status": "NOT_DERIVED",
        "captured_at_utc": "2026-09-19T15:00:00Z",
        "source": "API-Football /fixtures/players",
        "nationality_inference_allowed": "false",
        "travel_inference_allowed": "false",
        "research_only": "true",
        "operational_betting_authority": "false",
        "creates_signal": "false",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }


def player(player_id="1001", name="Completely Different PBK Name"):
    return {
        "player_id": player_id,
        "latest_observed_name": name,
        "latest_observed_position": "Midfielder",
        "latest_observed_age": "25",
        "latest_observed_number": "8",
        "latest_observed_photo_url": "",
        "first_seen_at_utc": "2026-09-01T00:00:00Z",
        "last_seen_at_utc": "2026-09-18T00:00:00Z",
        "latest_roster_seen_at_utc": "2026-09-18T00:00:00Z",
        "latest_stats_seen_at_utc": "",
        "roster_observation_rows": "1",
        "roster_team_count": "1",
        "latest_roster_team_ids": "999",
        "latest_roster_team_names": "PBK Club",
        "stats_fixture_count": "0",
        "stats_row_count": "0",
        "has_roster_evidence": "YES",
        "has_match_stats_evidence": "NO",
        "evidence_sources": "roster_history",
        "source": "stage80:roster_history+player_stats",
        "projection_version": j.CATALOG_VERSION,
    }


def transfer(player_id="1001", tm_id="777"):
    return {
        "pbk_player_id": player_id,
        "pbk_player_name": "Whatever",
        "transfermarkt_player_id": tm_id,
        "transfermarkt_player_name": "Another Name",
        "pbk_evidence_birth_date": "",
        "transfermarkt_date_of_birth": "2000-01-01",
        "mapping_method": "EXACT_NAME_CURRENT_CLUB",
        "mapping_confidence": "HIGH",
        "match_status": "AUTO_MATCH",
        "source": "stage80_transfer_entity_mapping",
        "mapping_version": "V3",
    }


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class InternationalDutyPlayerIdentityJoinTests(unittest.TestCase):
    def test_exact_player_id_join_ignores_name_mismatch(self):
        catalog, dup, conflicts = j.unique_map([player("1001")], "player_id")
        self.assertEqual((dup, conflicts), (0, 0))
        tmap, _, tconf = j.safe_transfer_map([transfer("1001", "777")])
        self.assertEqual(tconf, 0)

        rows, invalid = j.aggregate(
            [evidence("1001", "International Name")],
            catalog,
            tmap,
        )
        self.assertEqual(invalid, 0)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["pbk_catalog_match_status"], "EXACT_ID_MATCH")
        self.assertEqual(row["pbk_catalog_identity_method"], "API_FOOTBALL_PLAYER_ID_EXACT")
        self.assertEqual(row["transfermarkt_identity_status"], "SAFE_AUTO_HIGH")
        self.assertEqual(row["transfermarkt_player_id"], "777")
        self.assertEqual(row["fuzzy_matching_used"], "false")
        self.assertEqual(row["name_used_for_identity"], "false")
        self.assertEqual(row["club_at_fixture_date_status"], "NOT_DERIVED")

    def test_minutes_and_fixture_aggregation(self):
        rows = [
            evidence("1001", fixture="5001", minutes="90"),
            evidence("1001", fixture="5002", minutes="30"),
        ]
        rows[1]["kickoff_utc"] = "2025-09-08T18:45:00Z"
        rows[1]["provider_substitute_flag"] = "true"
        rows[1]["substitute_appearance_confirmed"] = "true"
        rows[1]["lineup_role"] = "SUBSTITUTE_APPEARANCE_PROVIDER_FLAG"

        out, invalid = j.aggregate(rows, {"1001": player("1001")}, {})
        self.assertEqual(invalid, 0)
        row = out[0]
        self.assertEqual(row["international_evidence_rows"], "2")
        self.assertEqual(row["international_fixture_count"], "2")
        self.assertEqual(row["appearance_fixture_count"], "2")
        self.assertEqual(row["minutes_confirmed_fixture_count"], "2")
        self.assertEqual(row["confirmed_minutes_total"], "120")
        self.assertEqual(row["substitute_appearance_fixture_count"], "1")
        self.assertEqual(row["first_international_kickoff_utc"], "2025-09-05T18:45:00Z")
        self.assertEqual(row["last_international_kickoff_utc"], "2025-09-08T18:45:00Z")

    def test_duplicate_historical_player_id_detected(self):
        _, duplicates, conflicts = j.unique_map(
            [player("1001", "A"), player("1001", "B")],
            "player_id",
        )
        self.assertEqual(duplicates, 1)
        self.assertEqual(conflicts, 1)

    def test_conflicting_safe_transfer_ids_fail_mapping(self):
        mapping, duplicate_rows, conflicts = j.safe_transfer_map([
            transfer("1001", "777"),
            transfer("1001", "888"),
        ])
        self.assertEqual(mapping, {})
        self.assertEqual(duplicate_rows, 1)
        self.assertEqual(conflicts, 1)

    def test_unsafe_transfer_identity_is_not_joined(self):
        bad = transfer("1001", "777")
        bad["mapping_confidence"] = "MEDIUM"
        mapping, _, conflicts = j.safe_transfer_map([bad])
        self.assertEqual(mapping, {})
        self.assertEqual(conflicts, 0)

    def test_invalid_evidence_governance_is_rejected(self):
        bad = evidence()
        bad["travel_status"] = "DERIVED"
        out, invalid = j.aggregate([bad], {"1001": player()}, {})
        self.assertEqual(out, [])
        self.assertEqual(invalid, 1)

    def test_run_materializes_exact_join(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evidence_path = root / "evidence.csv"
            evidence_meta_path = root / "evidence_meta.json"
            players_path = root / "players.csv"
            players_meta_path = root / "players_meta.json"
            transfer_path = root / "transfer.csv"
            output_path = root / "output.csv"
            meta_path = root / "meta.json"

            evidence_rows = [
                evidence("1001", "Intl A", "5001", "90"),
                evidence("1002", "Intl B", "5002", "45"),
                evidence("1003", "Intl C", "5003", "60"),
            ]
            write_csv(evidence_path, evidence_rows)
            write_csv(players_path, [
                player("1001", "PBK A"),
                player("1002", "PBK B"),
            ])
            write_csv(transfer_path, [
                transfer("1001", "777"),
                transfer("1003", "999"),
            ])

            evidence_meta_path.write_text(json.dumps({
                "version": j.EVIDENCE_VERSION,
                "status": "COLLECTING",
                "evidence_rows": 3,
                "duplicate_evidence_rows": 0,
                "invalid_evidence_rows": 0,
                "player_stats_starter_inference_allowed": False,
                "research_only": True,
                "operational_betting_authority": False,
            }), encoding="utf-8")
            players_meta_path.write_text(json.dumps({
                "version": j.CATALOG_VERSION,
                "status": "OK",
                "catalog_players": 2,
                "invalid_roster_rows": 0,
                "invalid_stats_rows": 0,
                "provider_calls": 0,
            }), encoding="utf-8")

            meta = j.run(
                evidence_path=evidence_path,
                evidence_meta_path=evidence_meta_path,
                players_path=players_path,
                players_meta_path=players_meta_path,
                transfer_identity_path=transfer_path,
                output_path=output_path,
                meta_path=meta_path,
            )
            self.assertEqual(meta["status"], "OK")
            self.assertEqual(meta["international_evidence_players"], 3)
            self.assertEqual(meta["exact_pbk_catalog_matched_players"], 2)
            self.assertEqual(meta["pbk_catalog_unmatched_players"], 1)
            self.assertAlmostEqual(meta["exact_pbk_catalog_player_coverage_pct"], 66.6667, places=4)
            self.assertEqual(meta["international_players_with_safe_transfer_identity"], 2)
            self.assertEqual(meta["international_players_with_catalog_and_transfer_identity"], 1)
            self.assertTrue(meta["exact_id_only"])
            self.assertFalse(meta["fuzzy_matching_used"])
            self.assertFalse(meta["name_used_for_identity"])
            self.assertFalse(meta["club_at_fixture_date_derived"])
            self.assertFalse(meta["current_club_substituted_for_historical_club"])
            self.assertEqual(meta["provider_calls"], 0)

            saved = j.read_csv(output_path)
            self.assertEqual(len(saved), 3)
            by = {r["player_id"]: r for r in saved}
            self.assertEqual(by["1001"]["pbk_catalog_match_status"], "EXACT_ID_MATCH")
            self.assertEqual(by["1002"]["transfermarkt_identity_status"], "UNMAPPED")
            self.assertEqual(by["1003"]["pbk_catalog_match_status"], "UNMATCHED")
            self.assertEqual(by["1003"]["transfermarkt_player_id"], "999")


if __name__ == "__main__":
    unittest.main()
