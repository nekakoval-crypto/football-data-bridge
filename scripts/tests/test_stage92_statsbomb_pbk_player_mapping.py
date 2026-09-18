import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage92_statsbomb_pbk_player_mapping as s92


class Stage92StatsBombPbkMappingTests(unittest.TestCase):
    def source_row(self, **overrides):
        row = {
            "record_id": "sb-record-1",
            "statsbomb_match_id": "100",
            "statsbomb_player_id": "9001",
            "player_name": "Manuel Akanji",
            "statsbomb_team_id": "77",
            "team_name": "Switzerland",
            "match_date": "2024-06-15",
            "competition_id": "55",
            "competition_name": "UEFA Euro",
            "season_id": "282",
            "season_name": "2024",
            "shots": "1",
            "non_penalty_shots": "1",
            "penalty_shots": "0",
            "xg_total": "0.250000000",
            "npxg": "0.250000000",
            "penalty_xg": "0.000000000",
            "assisted_shots": "1",
            "xa": "0.100000000",
            "source_event_sha256": "abc",
            "source_revision": "rev1",
        }
        row.update(overrides)
        return row

    def transfer_row(self, **overrides):
        row = {
            "pbk_player_id": "5",
            "pbk_player_name": "M. Akanji",
            "transfermarkt_player_id": "192565",
            "transfermarkt_player_name": "Manuel Akanji",
            "mapping_method": "EXACT_NAME_CURRENT_CLUB",
            "mapping_confidence": "HIGH",
        }
        row.update(overrides)
        return row

    def historical_row(self, **overrides):
        row = {
            "player_id": "5",
            "latest_observed_name": "M. Akanji",
        }
        row.update(overrides)
        return row

    def write_csv(self, path, rows):
        fields = list(rows[0].keys()) if rows else ["placeholder"]
        with Path(path).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_verified_transfer_full_name_is_auto_high(self):
        mapping = s92.build_mapping(
            [self.source_row()],
            [self.transfer_row()],
            [self.historical_row()],
        )
        self.assertEqual(len(mapping), 1)
        row = mapping[0]
        self.assertEqual(row["match_status"], "AUTO_MATCH")
        self.assertEqual(row["match_method"], s92.AUTO_METHOD)
        self.assertEqual(row["match_confidence"], "HIGH")
        self.assertEqual(row["pbk_player_id"], "5")
        self.assertEqual(row["transfermarkt_player_ids"], "192565")
        self.assertEqual(row["authoritative_for_player_xg_xa"], "true")

    def test_verified_stats_name_transfer_method_is_also_trusted(self):
        mapping = s92.build_mapping(
            [self.source_row()],
            [self.transfer_row(mapping_method="EXACT_STATS_NAME_CURRENT_CLUB")],
            [self.historical_row()],
        )
        self.assertEqual(mapping[0]["match_status"], "AUTO_MATCH")
        self.assertEqual(mapping[0]["match_confidence"], "HIGH")
        self.assertEqual(mapping[0]["pbk_player_id"], "5")

    def test_verified_profile_dob_transfer_method_is_also_trusted(self):
        mapping = s92.build_mapping(
            [self.source_row()],
            [self.transfer_row(mapping_method="EXACT_PROFILE_NAME_DOB_CURRENT_CLUB")],
            [self.historical_row()],
        )
        self.assertEqual(mapping[0]["match_status"], "AUTO_MATCH")
        self.assertEqual(mapping[0]["match_confidence"], "HIGH")
        self.assertEqual(mapping[0]["pbk_player_id"], "5")

    def test_auto_high_is_the_only_mapping_allowed_into_pbk_research_metrics(self):
        source = [self.source_row()]
        mapping = s92.build_mapping(
            source,
            [self.transfer_row()],
            [self.historical_row()],
        )
        mapped = s92.map_research_metrics(source, mapping)
        self.assertEqual(len(mapped), 1)
        row = mapped[0]
        self.assertEqual(row["pbk_player_id"], "5")
        self.assertEqual(row["statsbomb_player_id"], "9001")
        self.assertEqual(row["xg_total"], "0.250000000")
        self.assertEqual(row["xa"], "0.100000000")
        self.assertEqual(row["mapping_method"], s92.AUTO_METHOD)
        self.assertEqual(row["mapping_confidence"], "HIGH")
        self.assertEqual(row["operational_betting_authority"], "false")

    def test_initial_surname_unique_is_review_not_authority(self):
        source = [self.source_row(player_name="Achraf Hakimi", statsbomb_player_id="9002")]
        historical = [{"player_id": "9", "latest_observed_name": "A. Hakimi"}]
        mapping = s92.build_mapping(source, [], historical)
        row = mapping[0]
        self.assertEqual(row["match_status"], "REVIEW")
        self.assertEqual(row["match_method"], s92.REVIEW_METHOD)
        self.assertEqual(row["match_confidence"], "MEDIUM")
        self.assertEqual(row["pbk_player_id"], "9")
        self.assertEqual(row["authoritative_for_player_xg_xa"], "false")
        self.assertEqual(s92.map_research_metrics(source, mapping), [])

    def test_ambiguous_initial_surname_review_never_selects_pbk_id(self):
        source = [self.source_row(player_name="Alex Smith", statsbomb_player_id="9003")]
        historical = [
            {"player_id": "1", "latest_observed_name": "A. Smith"},
            {"player_id": "2", "latest_observed_name": "A. Smith"},
        ]
        row = s92.build_mapping(source, [], historical)[0]
        self.assertEqual(row["match_status"], "REVIEW")
        self.assertEqual(row["match_confidence"], "LOW")
        self.assertEqual(row["review_candidate_count"], 2)
        self.assertEqual(row["pbk_player_id"], "")
        self.assertEqual(row["authoritative_for_player_xg_xa"], "false")

    def test_same_full_name_linked_to_multiple_pbk_ids_is_not_auto(self):
        transfers = [
            self.transfer_row(pbk_player_id="5"),
            self.transfer_row(
                pbk_player_id="500",
                pbk_player_name="Other Akanji",
                transfermarkt_player_id="999999",
            ),
        ]
        row = s92.build_mapping([self.source_row()], transfers, [self.historical_row()])[0]
        self.assertNotEqual(row["match_status"], "AUTO_MATCH")
        self.assertEqual(row["authoritative_for_player_xg_xa"], "false")

    def test_transfer_rows_without_verified_stage80_mapping_are_ignored(self):
        transfers = [
            self.transfer_row(mapping_confidence="MEDIUM"),
            self.transfer_row(mapping_method="EXACT_NAME_UNIQUE"),
        ]
        row = s92.build_mapping([self.source_row()], transfers, [self.historical_row()])[0]
        self.assertEqual(row["match_status"], "REVIEW")
        self.assertFalse(row["authoritative_for_player_xg_xa"] == "true")

    def test_statsbomb_player_id_name_drift_forces_review(self):
        source = [
            self.source_row(player_name="Manuel Akanji"),
            self.source_row(
                record_id="sb-record-2",
                statsbomb_match_id="101",
                player_name="M. Akanji",
            ),
        ]
        row = s92.build_mapping(source, [self.transfer_row()], [self.historical_row()])[0]
        self.assertEqual(row["match_status"], "REVIEW")
        self.assertEqual(row["match_method"], "STATSBOMB_PLAYER_ID_NAME_DRIFT")
        self.assertEqual(row["match_confidence"], "LOW")
        self.assertEqual(row["authoritative_for_player_xg_xa"], "false")

    def test_normalization_is_unicode_and_case_stable_but_not_fuzzy(self):
        self.assertEqual(
            s92.normalized_name("  Christian  PULIŠIĆ "),
            s92.normalized_name("Christian Pulišić"),
        )
        self.assertNotEqual(
            s92.normalized_name("Christian Pulisic"),
            s92.normalized_name("Christian Pulišić"),
        )

    def test_run_waits_cleanly_without_stage91_materialization(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            transfers = root / "transfers.csv"
            historical = root / "historical.csv"
            source = root / "missing-source.csv"
            mapping_out = root / "mapping.csv"
            mapped_out = root / "mapped.csv"
            meta_out = root / "meta.json"
            self.write_csv(transfers, [self.transfer_row()])
            self.write_csv(historical, [self.historical_row()])

            meta = s92.run(
                source,
                transfers,
                historical,
                mapping_out,
                mapped_out,
                meta_out,
            )

            self.assertEqual(meta["status"], "WAITING_FOR_STAGE91_MATERIALIZATION")
            self.assertEqual(meta["mapping_rows"], 0)
            self.assertEqual(meta["mapped_research_rows"], 0)
            self.assertTrue(mapping_out.exists())
            self.assertTrue(mapped_out.exists())
            self.assertEqual(meta["provider_calls"], 0)

    def test_run_materializes_mapping_and_only_authoritative_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.csv"
            transfers = root / "transfers.csv"
            historical = root / "historical.csv"
            mapping_out = root / "mapping.csv"
            mapped_out = root / "mapped.csv"
            meta_out = root / "meta.json"

            source_rows = [
                self.source_row(),
                self.source_row(
                    record_id="sb-record-2",
                    statsbomb_player_id="9002",
                    player_name="Achraf Hakimi",
                ),
            ]
            self.write_csv(source, source_rows)
            self.write_csv(transfers, [self.transfer_row()])
            self.write_csv(
                historical,
                [
                    self.historical_row(),
                    {"player_id": "9", "latest_observed_name": "A. Hakimi"},
                ],
            )

            meta = s92.run(
                source,
                transfers,
                historical,
                mapping_out,
                mapped_out,
                meta_out,
            )

            with mapping_out.open(encoding="utf-8-sig", newline="") as stream:
                mapping = list(csv.DictReader(stream))
            with mapped_out.open(encoding="utf-8-sig", newline="") as stream:
                mapped = list(csv.DictReader(stream))

            self.assertEqual(meta["status"], "OK")
            self.assertEqual(meta["auto_match_high"], 1)
            self.assertEqual(meta["review"], 1)
            self.assertEqual(meta["mapped_research_rows"], 1)
            self.assertEqual(len(mapping), 2)
            self.assertEqual(len(mapped), 1)
            self.assertEqual(mapped[0]["pbk_player_id"], "5")
            self.assertFalse(meta["review_is_authoritative"])
            self.assertTrue(meta["mapped_output_requires_auto_high"])


if __name__ == "__main__":
    unittest.main()
