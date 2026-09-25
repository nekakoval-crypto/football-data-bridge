import gzip
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api_football_broker import ApiFootballBroker
from api_football_raw_archive import archive_response, payload_sha256, read_archived_response


class RawArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "archive"
        self.cache = Path(self.temp.name) / "cache.sqlite3"
        self.calls = []
        self.payload = {"response": [{"fixture": {"id": 123}, "players": [1, 2]}], "errors": []}
        self.env = patch.dict(os.environ, {"API_FOOTBALL_KEY": "super-secret-test-key"}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def transport(self, path, params, headers, timeout):
        self.calls.append((path, dict(params), dict(headers)))
        return 200, {"X-RateLimit-Remaining": "99"}, self.payload

    def broker(self, **kwargs):
        return ApiFootballBroker(
            transport=self.transport,
            cache_path=self.cache,
            archive_dir=self.root,
            sleep=lambda _: None,
            **kwargs,
        )

    def manifest_rows(self):
        path = self.root / "manifest.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_archive_writes_content_addressed_gzip_and_manifest(self):
        result = archive_response(
            root=self.root,
            request_key='["GET","/fixtures"]',
            path="/fixtures",
            normalized_params=(("id", "123"),),
            payload=self.payload,
            fetched_at=1_789_480_000,
        )
        self.assertTrue(result["blob_created"])
        self.assertTrue(result["manifest_appended"])
        self.assertEqual(result["payload_sha256"], payload_sha256(self.payload))
        blob = self.root / result["blob_path"]
        self.assertTrue(blob.exists())
        decoded = json.loads(gzip.decompress(blob.read_bytes()).decode("utf-8"))
        self.assertEqual(decoded, self.payload)
        rows = self.manifest_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["path"], "/fixtures")
        self.assertEqual(rows[0]["normalized_params"], [["id", "123"]])

    def test_broker_archives_only_real_provider_call_not_cache_hit(self):
        broker = self.broker()
        first = broker.get("/fixtures", {"id": 123}, ttl_seconds=3600)
        second = broker.get("/fixtures", {"id": 123}, ttl_seconds=3600)
        self.assertEqual(first, second)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.manifest_rows()), 1)
        stats = broker.stats()
        self.assertEqual(stats["real_api_calls"], 1)
        self.assertEqual(stats["provider_successes"], 1)
        self.assertEqual(stats["archive_write_successes"], 1)
        self.assertEqual(stats["archive_observations"], 1)
        self.assertTrue(stats["archive_enabled"])

    def test_same_exact_observation_is_manifest_idempotent_and_blob_deduplicated(self):
        broker = self.broker(default_ttl_seconds=0)
        with patch("api_football_broker._utc_timestamp", return_value=1_789_480_000.0):
            broker.get("/fixtures", {"id": 123}, force_refresh=True)
            broker.get("/fixtures", {"id": 123}, force_refresh=True)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(self.manifest_rows()), 1)
        stats = broker.stats()
        self.assertEqual(stats["archive_observations"], 1)
        self.assertEqual(stats["archive_manifest_dedup_hits"], 1)
        self.assertEqual(stats["archive_blob_dedup_hits"], 1)

    def test_distinct_real_observations_can_share_one_payload_blob(self):
        broker = self.broker(default_ttl_seconds=0)
        with patch("api_football_broker._utc_timestamp", side_effect=[1000.0, 1000.0, 1001.0, 1001.0]):
            broker.get("/fixtures", {"id": 123}, force_refresh=True)
            broker.get("/fixtures", {"id": 123}, force_refresh=True)
        rows = self.manifest_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["payload_sha256"], rows[1]["payload_sha256"])
        blobs = list((self.root / "blobs").rglob("*.json.gz"))
        self.assertEqual(len(blobs), 1)

    def test_archive_manifest_does_not_store_api_key_or_headers(self):
        broker = self.broker()
        broker.get("/fixtures/players", {"fixture": 123})
        raw_manifest = (self.root / "manifest.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("super-secret-test-key", raw_manifest)
        row = self.manifest_rows()[0]
        self.assertNotIn("headers", row)
        self.assertNotIn("api_key", row)
        self.assertEqual(row["path"], "/fixtures/players")


    def test_s3_request_index_supports_verified_archive_read(self):
        class Body:
            def __init__(self, value):
                self.value = value
            def read(self):
                return self.value

        class Missing(Exception):
            def __init__(self):
                self.response = {
                    "Error": {"Code": "NoSuchKey"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                }

        class FakeS3:
            def __init__(self):
                self.objects = {}
            def head_object(self, *, Bucket, Key):
                if Key not in self.objects:
                    raise Missing()
                return {}
            def put_object(self, *, Bucket, Key, Body, **kwargs):
                self.objects[Key] = Body
                return {}
            def get_object(self, *, Bucket, Key):
                if Key not in self.objects:
                    raise Missing()
                return {"Body": Body(self.objects[Key])}

        fake = FakeS3()
        env = {
            "PBK_RAW_ARCHIVE_S3_ACCESS_KEY_ID": "a",
            "PBK_RAW_ARCHIVE_S3_SECRET_ACCESS_KEY": "b",
            "PBK_RAW_ARCHIVE_S3_ENDPOINT": "https://example.invalid",
            "PBK_RAW_ARCHIVE_S3_BUCKET": "bucket",
            "PBK_RAW_ARCHIVE_S3_PREFIX": "test-archive",
        }
        key = '["GET","/fixtures/players",[["fixture","123"]]]'
        with patch.dict(os.environ, env, clear=False):
            result = archive_response(
                request_key=key,
                path="/fixtures/players",
                normalized_params=(("fixture", "123"),),
                payload=self.payload,
                fetched_at=1_789_480_000,
                s3_client=fake,
            )
            self.assertIn("request_index_path", result)
            restored = read_archived_response(key, client=fake)
        self.assertEqual(restored, self.payload)

    def test_archive_failure_is_telemetry_only_and_valid_provider_response_survives(self):
        bad_root = Path(self.temp.name) / "not-a-directory"
        bad_root.write_text("file blocks directory creation", encoding="utf-8")
        broker = ApiFootballBroker(
            transport=self.transport,
            cache_path=self.cache,
            archive_dir=bad_root,
            sleep=lambda _: None,
        )
        result = broker.get("/fixtures", {"id": 123})
        self.assertEqual(result, self.payload)
        self.assertEqual(broker.stats()["archive_errors"], 1)
        self.assertEqual(broker.stats()["provider_successes"], 1)
        self.assertEqual(broker.stats()["archive_write_successes"], 0)
        self.assertEqual(broker.stats()["real_api_calls"], 1)

    def test_provider_success_is_fully_accounted_as_archive_success_or_error(self):
        broker = self.broker()
        broker.get("/fixtures/players", {"fixture": 123})
        stats = broker.stats()
        self.assertEqual(
            stats["provider_successes"],
            stats["archive_write_successes"] + stats["archive_errors"],
        )

    def test_archive_is_disabled_when_no_storage_is_configured(self):
        with patch.dict(os.environ, {"API_FOOTBALL_KEY": "x", "API_FOOTBALL_ARCHIVE_DIR": ""}, clear=False):
            broker = ApiFootballBroker(
                transport=self.transport,
                cache_path=self.cache,
                sleep=lambda _: None,
            )
            broker.get("/fixtures", {"id": 123})
            self.assertFalse(broker.stats()["archive_enabled"])
            self.assertEqual(broker.stats()["archive_observations"], 0)


if __name__ == "__main__":
    unittest.main()
