from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_raw_archive_request_index as m


class RawArchiveRequestIndexTests(unittest.TestCase):
    def record(self, request_hash, fetched, payload="p", suffix="1"):
        return {
            "archive_version": "v",
            "request_key_sha256": request_hash,
            "path": "/fixtures/players",
            "normalized_params": [["fixture", suffix]],
            "fetched_at_utc": fetched,
            "payload_sha256": payload,
            "blob_key": f"blob/{payload}",
            "observation_key": f"obs/{suffix}",
        }

    def test_latest_observation_wins_per_exact_request(self):
        rows = [
            self.record("a", "2026-01-01T00:00:00Z", "old"),
            self.record("a", "2026-01-02T00:00:00Z", "new"),
            self.record("b", "2026-01-01T00:00:00Z", "b"),
        ]
        latest, invalid = m.latest_by_request(rows)
        self.assertEqual(invalid, 0)
        self.assertEqual(set(latest), {"a", "b"})
        self.assertEqual(latest["a"]["payload_sha256"], "new")

    def test_invalid_observation_is_fail_closed(self):
        latest, invalid = m.latest_by_request([
            self.record("a", "2026-01-01T00:00:00Z"),
            {"request_key_sha256": "broken"},
        ])
        self.assertEqual(set(latest), {"a"})
        self.assertEqual(invalid, 1)

    def test_index_payload_preserves_immutable_blob_pointer(self):
        record = self.record("abc", "2026-01-01T00:00:00Z", "hash")
        payload = m.index_payload(record)
        self.assertEqual(payload["request_key_sha256"], "abc")
        self.assertEqual(payload["payload_sha256"], "hash")
        self.assertEqual(payload["blob_key"], "blob/hash")
        self.assertEqual(payload["observation_key"], "obs/1")


if __name__ == "__main__":
    unittest.main()
