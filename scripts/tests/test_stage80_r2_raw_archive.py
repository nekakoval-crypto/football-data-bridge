import gzip
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api_football_broker import ApiFootballBroker
from api_football_raw_archive import (
    archive_response,
    s3_config_from_env,
    verify_s3_storage,
)


class FakeNotFound(Exception):
    def __init__(self):
        self.response = {
            "Error": {"Code": "404"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }


class FakeBody:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.puts = []
        self.gets = []

    def head_object(self, Bucket, Key):
        key = (Bucket, Key)
        if key not in self.objects:
            raise FakeNotFound()
        return {"ContentLength": len(self.objects[key]["Body"])}

    def put_object(self, Bucket, Key, Body, **kwargs):
        if hasattr(Body, "read"):
            Body = Body.read()
        if isinstance(Body, str):
            Body = Body.encode("utf-8")
        self.objects[(Bucket, Key)] = {"Body": bytes(Body), **kwargs}
        self.puts.append((Bucket, Key))
        return {"ETag": "fake"}

    def get_object(self, Bucket, Key):
        self.gets.append((Bucket, Key))
        return {"Body": FakeBody(self.objects[(Bucket, Key)]["Body"])}

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)
        return {}


class Stage80R2RawArchiveTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "PBK_RAW_ARCHIVE_S3_ACCESS_KEY_ID": "test-access",
            "PBK_RAW_ARCHIVE_S3_SECRET_ACCESS_KEY": "test-secret",
            "PBK_RAW_ARCHIVE_S3_ENDPOINT": "https://example.r2.cloudflarestorage.com",
            "PBK_RAW_ARCHIVE_S3_BUCKET": "pbk-api-football-raw",
            "PBK_RAW_ARCHIVE_S3_PREFIX": "api-football-raw",
            "API_FOOTBALL_ARCHIVE_DIR": "",
            "API_FOOTBALL_KEY": "provider-test-key",
        }
        self.payload = {"response": [{"fixture": {"id": 123}}], "errors": []}

    def test_complete_s3_config_is_detected(self):
        with patch.dict(os.environ, self.env, clear=False):
            cfg = s3_config_from_env()
        self.assertEqual(cfg["bucket"], "pbk-api-football-raw")
        self.assertEqual(cfg["region"], "auto")
        self.assertEqual(cfg["prefix"], "api-football-raw")

    def test_partial_s3_config_is_rejected(self):
        env = dict(self.env)
        env["PBK_RAW_ARCHIVE_S3_SECRET_ACCESS_KEY"] = ""
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaisesRegex(RuntimeError, "Incomplete raw archive S3 configuration"):
                s3_config_from_env()

    def test_s3_archive_is_content_addressed_and_idempotent(self):
        fake = FakeS3()
        with patch.dict(os.environ, self.env, clear=False):
            first = archive_response(
                root=None,
                request_key='["GET","/fixtures"]',
                path="/fixtures",
                normalized_params=(("id", "123"),),
                payload=self.payload,
                fetched_at=1789480000,
                s3_client=fake,
            )
            second = archive_response(
                root=None,
                request_key='["GET","/fixtures"]',
                path="/fixtures",
                normalized_params=(("id", "123"),),
                payload=self.payload,
                fetched_at=1789480000,
                s3_client=fake,
            )

        self.assertEqual(first["backend"], "S3")
        self.assertTrue(first["blob_created"])
        self.assertTrue(first["manifest_appended"])
        self.assertFalse(second["blob_created"])
        self.assertFalse(second["manifest_appended"])
        self.assertIn("/blobs/sha256/", first["blob_path"])
        self.assertIn("/observations/", first["observation_path"])

        blob = fake.objects[("pbk-api-football-raw", first["blob_path"])]["Body"]
        decoded = json.loads(gzip.decompress(blob).decode("utf-8"))
        self.assertEqual(decoded, self.payload)

        obs = json.loads(
            fake.objects[("pbk-api-football-raw", first["observation_path"])]["Body"].decode("utf-8")
        )
        self.assertEqual(obs["path"], "/fixtures")
        self.assertEqual(obs["storage_backend"], "S3")
        self.assertNotIn("provider-test-key", json.dumps(obs))

    def test_storage_verify_does_write_readback_hash(self):
        fake = FakeS3()
        with patch.dict(os.environ, self.env, clear=False):
            result = verify_s3_storage(client=fake, keep_object=True)
        self.assertEqual(result["status"], "READY")
        self.assertTrue(result["readback_match"])
        self.assertTrue(result["durable"])
        self.assertEqual(len(fake.puts), 1)
        self.assertEqual(len(fake.gets), 1)
        self.assertIn("/healthchecks/", result["object_key"])

    def test_broker_enables_s3_archive_without_local_dir(self):
        fake = FakeS3()
        calls = []

        def transport(path, params, headers, timeout):
            calls.append(path)
            return 200, {}, self.payload

        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, self.env, clear=False):
            broker = ApiFootballBroker(
                transport=transport,
                cache_path=Path(td) / "cache.sqlite3",
                sleep=lambda _: None,
            )
            with patch("api_football_raw_archive._s3_client", return_value=fake):
                result = broker.get("/fixtures", {"id": 123}, ttl_seconds=0)

        self.assertEqual(result, self.payload)
        self.assertEqual(calls, ["/fixtures"])
        stats = broker.stats()
        self.assertTrue(stats["archive_enabled"])
        self.assertEqual(stats["archive_backend"], "S3")
        self.assertEqual(stats["archive_observations"], 1)
        self.assertEqual(stats["archive_errors"], 0)
        self.assertIn("/observations/", stats["archive_last_observation_path"])
        self.assertIn("/blobs/sha256/", stats["archive_last_blob_path"])
        self.assertTrue(stats["archive_last_payload_sha256"])


if __name__ == "__main__":
    unittest.main()
