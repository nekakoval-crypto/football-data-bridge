import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage91_statsbomb_player_xg_xa as s91


class Stage91StatsBombPlayerXgXaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.events = self.root / "events"
        self.matches = self.root / "matches"
        self.events.mkdir()
        self.matches.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_events(self, match_id, rows):
        path = self.events / f"{match_id}.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        return path

    def write_matches(self, rows):
        path = self.matches / "competition.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        return path

    def base_pass(self, event_id="pass-1", player_id=20, player_name="Creator", team_id=1):
        return {
            "id": event_id,
            "type": {"name": "Pass"},
            "player": {"id": player_id, "name": player_name},
            "team": {"id": team_id, "name": "Alpha"},
            "pass": {"shot_assist": True},
        }

    def base_shot(
        self,
        event_id="shot-1",
        player_id=10,
        player_name="Shooter",
        team_id=1,
        xg=0.2,
        key_pass_id="pass-1",
        shot_type="Open Play",
    ):
        return {
            "id": event_id,
            "type": {"name": "Shot"},
            "player": {"id": player_id, "name": player_name},
            "team": {"id": team_id, "name": "Alpha" if team_id == 1 else "Beta"},
            "shot": {
                "statsbomb_xg": xg,
                "key_pass_id": key_pass_id,
                "type": {"name": shot_type},
            },
        }

    def test_xg_is_source_metric_and_xa_is_created_shot_xg(self):
        path = self.write_events(
            "100",
            [
                self.base_pass(),
                self.base_shot(xg=0.2),
                self.base_shot(
                    event_id="shot-2",
                    xg=0.76,
                    key_pass_id=None,
                    shot_type="Penalty",
                ),
            ],
        )
        rows, meta = s91.project_event_file(path, source_revision="abc123")
        by_player = {row["statsbomb_player_id"]: row for row in rows}

        shooter = by_player["10"]
        creator = by_player["20"]

        self.assertEqual(shooter["shots"], 2)
        self.assertEqual(shooter["non_penalty_shots"], 1)
        self.assertEqual(shooter["penalty_shots"], 1)
        self.assertEqual(shooter["xg_total"], "0.960000000")
        self.assertEqual(shooter["npxg"], "0.200000000")
        self.assertEqual(shooter["penalty_xg"], "0.760000000")
        self.assertEqual(shooter["xa"], "0.000000000")

        self.assertEqual(creator["shots"], 0)
        self.assertEqual(creator["assisted_shots"], 1)
        self.assertEqual(creator["xa"], "0.200000000")
        self.assertEqual(creator["xg_source_field"], "shot.statsbomb_xg")
        self.assertEqual(
            creator["xa_derivation_method"],
            s91.XA_METHOD,
        )
        self.assertEqual(creator["source_revision"], "abc123")
        self.assertEqual(meta["xg_shots"], 2)
        self.assertEqual(meta["xa_links"], 1)

    def test_zero_xg_is_valid_not_missing(self):
        path = self.write_events(
            "101",
            [self.base_shot(xg=0.0, key_pass_id=None)],
        )
        rows, meta = s91.project_event_file(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["xg_total"], "0.000000000")
        self.assertEqual(rows[0]["npxg"], "0.000000000")
        self.assertEqual(meta["xg_shots"], 1)
        self.assertEqual(meta["invalid_xg_shots"], 0)

    def test_invalid_xg_is_skipped_not_zero_filled(self):
        path = self.write_events(
            "102",
            [self.base_shot(xg=None, key_pass_id=None)],
        )
        rows, meta = s91.project_event_file(path)
        self.assertEqual(rows, [])
        self.assertEqual(meta["xg_shots"], 0)
        self.assertEqual(meta["invalid_xg_shots"], 1)

    def test_cross_team_key_pass_never_receives_xa(self):
        creator = self.base_pass(team_id=2)
        creator["team"]["name"] = "Beta"
        path = self.write_events(
            "103",
            [creator, self.base_shot(team_id=1, xg=0.33)],
        )
        rows, meta = s91.project_event_file(path)
        by_player = {row["statsbomb_player_id"]: row for row in rows}
        self.assertNotIn("20", by_player)
        self.assertEqual(by_player["10"]["xg_total"], "0.330000000")
        self.assertEqual(meta["xa_links"], 0)
        self.assertEqual(meta["xa_team_mismatch"], 1)

    def test_unmatched_key_pass_is_reported(self):
        path = self.write_events(
            "104",
            [self.base_shot(xg=0.18, key_pass_id="missing-pass")],
        )
        rows, meta = s91.project_event_file(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["xa"], "0.000000000")
        self.assertEqual(meta["xa_unmatched"], 1)

    def test_run_enriches_match_metadata_and_writes_derived_only_csv(self):
        self.write_matches(
            [{
                "match_id": 105,
                "match_date": "2024-06-18",
                "competition": {
                    "competition_id": 55,
                    "competition_name": "UEFA Euro",
                },
                "season": {
                    "season_id": 282,
                    "season_name": "2024",
                },
            }]
        )
        self.write_events("105", [self.base_shot(xg=0.25, key_pass_id=None)])
        out = self.root / "player_xg_xa.csv"
        meta_out = self.root / "meta.json"

        result = s91.run(
            self.events,
            self.matches,
            out,
            meta_out,
            source_revision="revision-1",
        )

        with out.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_date"], "2024-06-18")
        self.assertEqual(rows[0]["competition_name"], "UEFA Euro")
        self.assertEqual(rows[0]["season_name"], "2024")
        self.assertTrue(rows[0]["source_event_sha256"])
        self.assertEqual(rows[0]["attribution_required"], "true")
        self.assertEqual(rows[0]["research_only"], "true")
        self.assertEqual(rows[0]["operational_betting_authority"], "false")
        self.assertFalse(result["raw_data_committed_to_pbk"])
        self.assertEqual(result["pbk_identity_mapping"], "NOT_IMPLEMENTED")
        self.assertEqual(result["provider_calls"], 0)

    def test_record_identity_is_deterministic(self):
        path = self.write_events(
            "106",
            [self.base_shot(xg=0.4, key_pass_id=None)],
        )
        first, _ = s91.project_event_file(path)
        second, _ = s91.project_event_file(path)
        self.assertEqual(first[0]["record_id"], second[0]["record_id"])
        self.assertEqual(first[0]["source_event_sha256"], second[0]["source_event_sha256"])


if __name__ == "__main__":
    unittest.main()
