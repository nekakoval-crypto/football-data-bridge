import io
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import stage91_derived_artifact_r2 as a


class FakeBody:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[(Bucket, Key)] = Body
        return {}

    def get_object(self, Bucket, Key):
        return {"Body": FakeBody(self.objects[(Bucket, Key)])}


class Stage91DerivedArtifactR2Tests(unittest.TestCase):
    def config(self):
        return {
            "bucket": "pbk",
            "prefix": "pbk-derived-research",
            "endpoint": "https://example.invalid",
            "access_key_id": "x",
            "secret_access_key": "y",
            "region": "auto",
        }

    def test_upload_then_fetch_round_trip(self):
        client = FakeS3()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.csv"
            destination = root / "restored.csv"
            source.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

            uploaded = a.upload(
                source,
                source_revision="abc123",
                config=self.config(),
                client=client,
            )
            fetched = a.fetch(
                destination,
                config=self.config(),
                client=client,
            )

            self.assertEqual(destination.read_bytes(), source.read_bytes())
            self.assertEqual(uploaded["sha256"], fetched["sha256"])
            self.assertEqual(uploaded["rows"], 2)
            self.assertTrue(fetched["verified"])
            self.assertFalse(fetched["raw_statsbomb_events_stored"])
            self.assertTrue(fetched["research_only"])
            self.assertFalse(fetched["operational_betting_authority"])

    def test_fetch_rejects_hash_mismatch(self):
        client = FakeS3()
        config = self.config()
        manifest = {
            "version": a.VERSION,
            "artifact": "ops/statsbomb_player_xg_xa.csv",
            "sha256": "0" * 64,
            "bytes": 4,
            "rows": 1,
            "source_revision": "abc",
            "object_key": "artifact.csv.gz",
            "created_at_utc": "2026-09-26T00:00:00Z",
            "raw_statsbomb_events_stored": False,
            "research_only": True,
            "operational_betting_authority": False,
        }
        import gzip

        client.objects[(config["bucket"], a.pointer_key(config))] = json.dumps(manifest).encode()
        client.objects[(config["bucket"], "artifact.csv.gz")] = gzip.compress(b"x\ny\n", mtime=0)

        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                a.fetch(
                    Path(temp) / "restored.csv",
                    config=config,
                    client=client,
                )


if __name__ == "__main__":
    unittest.main()
