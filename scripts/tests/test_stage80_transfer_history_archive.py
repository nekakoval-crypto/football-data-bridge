import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage80_transfer_history_archive import (
    merge_first_observation,
    normalize_mapped_rows,
    run,
)


class Stage80TransferHistoryArchiveTests(unittest.TestCase):
    def mapping_row(self, status="AUTO_MATCH", method="EXACT_NAME_CURRENT_CLUB", confidence="HIGH"):
        return {
            "pbk_player_id": "11",
            "pbk_player_name": "Player One",
            "transfermarkt_player_id": "900",
            "transfermarkt_player_name": "Player One",
            "match_status": status,
            "match_method": method,
            "match_confidence": confidence,
        }

    def mapped_row(self, **overrides):
        row = {
            "pbk_player_id": "11",
            "transfermarkt_player_id": "900",
            "player_name": "Player One",
            "transfer_date": "2024-07-01",
            "transfer_season": "24/25",
            "from_club_id": "100",
            "from_club_name": "Old Club",
            "to_club_id": "200",
            "to_club_name": "New Club",
            "transfer_fee": "",
            "market_value_in_eur": "",
            "mapping_method": "EXACT_NAME_CURRENT_CLUB",
            "mapping_confidence": "HIGH",
            "source": "dcaribou/transfermarkt-datasets:transfers",
        }
        row.update(overrides)
        return row

    def write_csv(self, path, fields, rows):
        with Path(path).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_auto_match_high_is_persisted_and_namespaces_remain_separate(self):
        rows, rejected, invalid = normalize_mapped_rows(
            [self.mapped_row()],
            [self.mapping_row()],
            source_snapshot="2026-07-06",
            metadata_sha="abc",
            ingested_at_utc="2026-09-18T13:00:00Z",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rejected, 0)
        self.assertEqual(invalid, 0)
        self.assertEqual(rows[0]["pbk_player_id"], "11")
        self.assertEqual(rows[0]["transfermarkt_player_id"], "900")
        self.assertNotEqual(rows[0]["pbk_player_id"], rows[0]["transfermarkt_player_id"])
        self.assertEqual(rows[0]["pbk_player_name"], "Player One")
        self.assertEqual(rows[0]["source_snapshot"], "2026-07-06")
        self.assertTrue(rows[0]["transfer_event_id"])

    def test_stats_name_auto_high_is_persisted(self):
        rows, rejected, invalid = normalize_mapped_rows(
            [self.mapped_row(mapping_method="EXACT_STATS_NAME_CURRENT_CLUB")],
            [self.mapping_row(method="EXACT_STATS_NAME_CURRENT_CLUB")],
            source_snapshot="snap",
            metadata_sha="abc",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rejected, 0)
        self.assertEqual(invalid, 0)
        self.assertEqual(rows[0]["mapping_method"], "EXACT_STATS_NAME_CURRENT_CLUB")

    def test_profile_name_dob_auto_high_is_persisted(self):
        rows, rejected, invalid = normalize_mapped_rows(
            [self.mapped_row(mapping_method="EXACT_PROFILE_NAME_DOB_CURRENT_CLUB")],
            [self.mapping_row(method="EXACT_PROFILE_NAME_DOB_CURRENT_CLUB")],
            source_snapshot="snap",
            metadata_sha="abc",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rejected, 0)
        self.assertEqual(invalid, 0)
        self.assertEqual(rows[0]["mapping_method"], "EXACT_PROFILE_NAME_DOB_CURRENT_CLUB")

    def test_review_mapping_is_not_authoritative_transfer_evidence(self):
        rows, rejected, invalid = normalize_mapped_rows(
            [self.mapped_row()],
            [self.mapping_row(status="REVIEW", method="EXACT_NAME_UNIQUE", confidence="MEDIUM")],
            source_snapshot="snap",
            metadata_sha="abc",
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected, 1)
        self.assertEqual(invalid, 0)

    def test_missing_optional_values_stay_empty_not_zero_filled(self):
        rows, _, _ = normalize_mapped_rows(
            [self.mapped_row(transfer_fee="", market_value_in_eur="", from_club_id="", to_club_id="")],
            [self.mapping_row()],
            source_snapshot="snap",
            metadata_sha="abc",
        )
        self.assertEqual(rows[0]["transfer_fee"], "")
        self.assertEqual(rows[0]["market_value_in_eur"], "")
        self.assertEqual(rows[0]["from_club_id"], "")
        self.assertEqual(rows[0]["to_club_id"], "")

    def test_merge_is_idempotent_and_does_not_duplicate_event(self):
        candidate, _, _ = normalize_mapped_rows(
            [self.mapped_row()],
            [self.mapping_row()],
            source_snapshot="snap",
            metadata_sha="abc",
            ingested_at_utc="2026-09-18T13:00:00Z",
        )
        first, meta1 = merge_first_observation([], candidate)
        second, meta2 = merge_first_observation(first, candidate)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(meta1["added_rows"], 1)
        self.assertEqual(meta2["added_rows"], 0)
        self.assertGreaterEqual(meta2["duplicate_rows"], 1)

    def test_new_source_snapshot_without_fact_change_is_idempotent(self):
        candidate, _, _ = normalize_mapped_rows(
            [self.mapped_row()],
            [self.mapping_row()],
            source_snapshot="snap-a",
            metadata_sha="aaa",
            ingested_at_utc="2026-09-18T13:00:00Z",
        )
        first, _ = merge_first_observation([], candidate)
        same_facts = dict(candidate[0])
        same_facts["source_snapshot"] = "snap-b"
        same_facts["source_metadata_sha256"] = "bbb"
        same_facts["ingested_at_utc"] = "2026-09-19T13:00:00Z"
        second, meta = merge_first_observation(first, [same_facts])
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["source_snapshot"], "snap-a")
        self.assertEqual(meta["conflicts_preserved_first_observation"], 0)
        self.assertGreaterEqual(meta["duplicate_rows"], 1)

    def test_conflicting_repeat_preserves_first_observation(self):
        candidate, _, _ = normalize_mapped_rows(
            [self.mapped_row(transfer_fee="100")],
            [self.mapping_row()],
            source_snapshot="snap-a",
            metadata_sha="aaa",
            ingested_at_utc="2026-09-18T13:00:00Z",
        )
        first, _ = merge_first_observation([], candidate)
        changed = dict(candidate[0])
        changed["transfer_fee"] = "200"
        changed["source_snapshot"] = "snap-b"
        changed["source_metadata_sha256"] = "bbb"
        second, meta = merge_first_observation(first, [changed])
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["transfer_fee"], "100")
        self.assertEqual(second[0]["source_snapshot"], "snap-a")
        self.assertEqual(meta["conflicts_preserved_first_observation"], 1)

    def test_end_to_end_rerun_keeps_single_event(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mapped = root / "mapped.csv"
            mapping = root / "mapping.csv"
            metadata = root / "dataset-metadata.json"
            out = root / "historical_transfer_events.csv"
            meta = root / "last_run.json"

            self.write_csv(mapped, list(self.mapped_row().keys()), [self.mapped_row()])
            self.write_csv(mapping, list(self.mapping_row().keys()), [self.mapping_row()])
            metadata.write_text(json.dumps({"snapshot_date": "2026-07-06"}), encoding="utf-8")

            first = run(mapped, mapping, metadata, None, out, meta)
            second = run(mapped, mapping, metadata, out, out, meta)

            with out.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))

            self.assertEqual(first["archive_rows"], 1)
            self.assertEqual(second["archive_rows"], 1)
            self.assertEqual(second["added_rows"], 0)
            self.assertEqual(len(rows), 1)
            self.assertFalse(second["creates_signal"])
            self.assertFalse(second["probability_mutation"])
            self.assertFalse(second["current_operational_authority"])


    def test_run_metadata_describes_all_safe_identity_methods(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mapped = root / "mapped.csv"
            mapping = root / "mapping.csv"
            metadata = root / "dataset-metadata.json"
            out = root / "historical_transfer_events.csv"
            meta = root / "last_run.json"

            mapped_row = self.mapped_row(mapping_method="EXACT_INTERNATIONAL_NAME_PROFILE_DOB")
            mapping_row = self.mapping_row(method="EXACT_INTERNATIONAL_NAME_PROFILE_DOB")
            self.write_csv(mapped, list(mapped_row.keys()), [mapped_row])
            self.write_csv(mapping, list(mapping_row.keys()), [mapping_row])
            metadata.write_text(json.dumps({"snapshot_date":"2026-07-06"}), encoding="utf-8")

            result = run(mapped, mapping, metadata, None, out, meta)

            self.assertEqual(
                result["version"],
                "PBK_STAGE80_TRANSFER_HISTORY_ARCHIVE_V4_INTERNATIONAL_NAME_PROFILE_DOB",
            )
            self.assertIn("EXACT_INTERNATIONAL_NAME_PROFILE_DOB", result["mapping_policy"])

    def test_international_name_profile_dob_mapping_is_safe_for_archive(self):
        mapping=[{
            "pbk_player_id":"1100","pbk_player_name":"Erling Haaland",
            "transfermarkt_player_id":"418560","transfermarkt_player_name":"Erling Haaland",
            "match_method":"EXACT_INTERNATIONAL_NAME_PROFILE_DOB",
            "match_status":"AUTO_MATCH","match_confidence":"HIGH",
        }]
        mapped=[{
            "pbk_player_id":"1100","transfermarkt_player_id":"418560",
            "player_name":"Erling Haaland","transfer_date":"2022-07-01",
            "transfer_season":"22/23","from_club_id":"27","from_club_name":"Dortmund",
            "to_club_id":"281","to_club_name":"Manchester City",
            "mapping_method":"EXACT_INTERNATIONAL_NAME_PROFILE_DOB",
            "mapping_confidence":"HIGH",
        }]
        rows,rejected,invalid=normalize_mapped_rows(mapped,mapping)
        self.assertEqual(len(rows),1)
        self.assertEqual(rejected,0)
        self.assertEqual(invalid,0)
        self.assertEqual(rows[0]["mapping_method"],"EXACT_INTERNATIONAL_NAME_PROFILE_DOB")



if __name__ == "__main__":
    unittest.main()
