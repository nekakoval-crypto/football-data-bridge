import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.pbk_team_style_evidence import (
    append_evidence,
    extract_archive_evidence,
    normalized_import_row,
)


class TeamStyleEvidenceTests(unittest.TestCase):
    def _write_obs(self, root: Path, obs_id: str, path: str, params, payload, fetched: str):
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        blob = root / "blobs" / digest[:2] / f"{digest}.json.gz"
        blob.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(blob, "wb") as stream:
            stream.write(raw)
        record = {
            "archive_version": "PBK_STAGE80_RAW_API_ARCHIVE_V1",
            "observation_id": obs_id,
            "provider": "api-football",
            "method": "GET",
            "path": path,
            "normalized_params": params,
            "fetched_at_utc": fetched,
            "payload_sha256": digest,
            "blob_path": blob.relative_to(root).as_posix(),
        }
        with (root / "manifest.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")

    def _fixture_payload(self):
        return {
            "response": [
                {
                    "fixture": {"id": 101, "date": "2026-09-10T18:00:00+00:00"},
                    "teams": {
                        "home": {"id": 1, "name": "Home FC"},
                        "away": {"id": 2, "name": "Away FC"},
                    },
                }
            ]
        }

    def _stats_payload(self):
        return {
            "response": [
                {
                    "team": {"id": 1, "name": "Home FC"},
                    "statistics": [
                        {"type": "Total Shots", "value": 14},
                        {"type": "Shots on Goal", "value": 6},
                        {"type": "Ball Possession", "value": "61%"},
                        {"type": "Corner Kicks", "value": 7},
                        {"type": "Expected Goals", "value": "1.82"},
                    ],
                },
                {
                    "team": {"id": 2, "name": "Away FC"},
                    "statistics": [
                        {"type": "Total Shots", "value": 8},
                        {"type": "Ball Possession", "value": "39%"},
                    ],
                },
            ]
        }

    def test_archive_stats_become_two_team_rows_with_explicit_venue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_obs(root, "fx", "/fixtures", [["id", "101"]], self._fixture_payload(), "2026-09-10T17:00:00Z")
            self._write_obs(root, "st", "/fixtures/statistics", [["fixture", "101"]], self._stats_payload(), "2026-09-10T20:00:00Z")
            rows, meta = extract_archive_evidence(root)
            self.assertEqual(meta["provider_calls_added"], 0)
            self.assertEqual(meta["statistics_observations"], 1)
            self.assertEqual(len(rows), 2)
            home = next(row for row in rows if row["team_id"] == 1)
            away = next(row for row in rows if row["team_id"] == 2)
            self.assertEqual(home["venue"], "HOME")
            self.assertEqual(away["venue"], "AWAY")
            self.assertEqual(home["metrics"]["shots_for"], 14.0)
            self.assertEqual(home["metrics"]["possession_pct"], 61.0)
            self.assertEqual(home["metrics"]["xg_for"], 1.82)
            self.assertNotIn("shots_on_target_for", away["metrics"])
            self.assertEqual(home["observed_at_utc"], "2026-09-10T20:00:00+00:00")

    def test_statistics_without_fixture_metadata_are_not_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_obs(root, "st", "/fixtures/statistics", [["fixture", "101"]], self._stats_payload(), "2026-09-10T20:00:00Z")
            rows, meta = extract_archive_evidence(root)
            self.assertEqual(rows, [])
            self.assertEqual(meta["exclusions"]["MISSING_FIXTURE_METADATA"], 1)

    def test_append_is_idempotent_by_observation_fixture_team(self):
        row = {
            "source_observation_id": "obs",
            "fixture_id": 1,
            "team_id": 2,
            "schema_version": "PBK_TEAM_STYLE_EVIDENCE_V1",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.jsonl"
            first = append_evidence([row], path)
            second = append_evidence([row], path)
            self.assertEqual(first["rows_added"], 1)
            self.assertEqual(second["rows_added"], 0)
            self.assertEqual(second["duplicates_skipped"], 1)
            self.assertEqual(len(path.read_text(encoding="utf-8").strip().splitlines()), 1)

    def test_normalized_import_requires_aware_times_and_explicit_venue(self):
        base = {
            "source_observation_id": "hist-1",
            "fixture_id": 1,
            "team_id": 10,
            "venue": "HOME",
            "kickoff_utc": "2026-09-01T18:00:00+00:00",
            "observed_at_utc": "2026-09-01T20:00:00+00:00",
            "metrics": {"shots_for": 12, "xg_for": None},
        }
        accepted = normalized_import_row(base)
        self.assertIsNotNone(accepted)
        self.assertEqual(accepted["metrics"], {"shots_for": 12.0})
        naive = dict(base, observed_at_utc="2026-09-01T20:00:00")
        self.assertIsNone(normalized_import_row(naive))
        unknown_venue = dict(base, venue="NEUTRAL")
        self.assertIsNone(normalized_import_row(unknown_venue))


if __name__ == "__main__":
    unittest.main()
