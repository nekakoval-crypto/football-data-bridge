#!/usr/bin/env python3
"""One-call production integration probe for API-Football -> broker -> R2 archive.

Uses API-Football /status to minimize cost and avoid affecting match research.
The probe requires exactly one real provider call, then reads the just-archived
observation and gzip blob back from S3/R2 and verifies payload SHA-256.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from api_football_broker import ApiFootballBroker
from api_football_raw_archive import canonical_payload_bytes, s3_config_from_env, _s3_client

OPS = Path(os.getenv("OPS_DIR", "ops"))
OUT = OPS / "stage80_raw_archive_provider_probe_last_run.json"
VERSION = "PBK_STAGE80_RAW_ARCHIVE_PROVIDER_PROBE_V1"


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    broker = ApiFootballBroker(default_ttl_seconds=0, attempts=2)
    payload = broker.get("/status", {}, ttl_seconds=0, force_refresh=True)
    stats = broker.stats()

    if stats.get("real_api_calls") != 1:
        raise RuntimeError(f"Expected exactly one real provider call, got {stats.get('real_api_calls')}")
    if not stats.get("archive_enabled"):
        raise RuntimeError("Raw archive is not enabled")
    if stats.get("archive_backend") != "S3":
        raise RuntimeError(f"Expected S3 archive backend, got {stats.get('archive_backend')}")
    if stats.get("archive_errors"):
        raise RuntimeError(f"Archive reported errors: {stats.get('archive_errors')}")

    observation_key = stats.get("archive_last_observation_path")
    blob_key = stats.get("archive_last_blob_path")
    expected_hash = stats.get("archive_last_payload_sha256")
    if not observation_key or not blob_key or not expected_hash:
        raise RuntimeError("Broker did not expose archived object paths/hash")

    cfg = s3_config_from_env()
    client = _s3_client(cfg)

    observation_bytes = client.get_object(Bucket=cfg["bucket"], Key=observation_key)["Body"].read()
    observation = json.loads(observation_bytes.decode("utf-8"))
    blob_bytes = client.get_object(Bucket=cfg["bucket"], Key=blob_key)["Body"].read()
    raw_payload = gzip.decompress(blob_bytes)

    canonical = canonical_payload_bytes(payload)
    provider_hash = hashlib.sha256(canonical).hexdigest()
    readback_hash = hashlib.sha256(raw_payload).hexdigest()

    checks = {
        "provider_hash_matches_broker": provider_hash == expected_hash,
        "blob_readback_hash_matches": readback_hash == expected_hash,
        "blob_payload_matches_provider": raw_payload == canonical,
        "observation_hash_matches": observation.get("payload_sha256") == expected_hash,
        "observation_path_is_status": observation.get("path") == "/status",
        "observation_backend_is_s3": observation.get("storage_backend") == "S3",
    }
    ready = all(checks.values())
    report = {
        "version": VERSION,
        "run_at_utc": now.isoformat().replace("+00:00", "Z"),
        "status": "READY" if ready else "ATTENTION",
        "provider_endpoint": "/status",
        "provider_calls": stats.get("real_api_calls"),
        "archive_enabled": stats.get("archive_enabled"),
        "archive_backend": stats.get("archive_backend"),
        "archive_observations": stats.get("archive_observations"),
        "archive_errors": stats.get("archive_errors"),
        "observation_key": observation_key,
        "blob_key": blob_key,
        "payload_sha256": expected_hash,
        "checks": checks,
        "durable_provider_roundtrip": ready,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    OPS.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if not ready:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
