#!/usr/bin/env python3
"""Backfill fast request-index pointers for existing PBK R2 raw observations.

Provider-free. Reads immutable observation metadata already stored in R2 and
writes one mutable request-index pointer per exact API-Football request key.
Payload blobs are not downloaded and API-Football is never called.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from api_football_raw_archive import (
    ARCHIVE_VERSION,
    _request_index_key,
    _s3_client,
    s3_config_from_env,
)

OPS = Path(os.getenv("OPS_DIR", "ops"))
META = OPS / "stage80_raw_archive_request_index_last_run.json"
VERSION = "PBK_STAGE80_RAW_ARCHIVE_REQUEST_INDEX_V1"


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iter_observation_keys(client, bucket, prefix):
    paginator = client.get_paginator("list_objects_v2")
    root = f"{prefix}/observations/"
    for page in paginator.paginate(Bucket=bucket, Prefix=root):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if key.endswith(".json"):
                yield key


def valid_record(record):
    return (
        isinstance(record, dict)
        and bool(str(record.get("request_key_sha256") or ""))
        and bool(str(record.get("payload_sha256") or ""))
        and bool(str(record.get("blob_key") or ""))
        and bool(str(record.get("observation_key") or ""))
        and bool(str(record.get("fetched_at_utc") or ""))
    )


def latest_by_request(records):
    latest = {}
    invalid = 0
    for record in records:
        if not valid_record(record):
            invalid += 1
            continue
        request_hash = str(record["request_key_sha256"])
        current = latest.get(request_hash)
        if current is None or str(record["fetched_at_utc"]) > str(current["fetched_at_utc"]):
            latest[request_hash] = dict(record)
    return latest, invalid


def index_payload(record):
    return {
        "archive_version": str(record.get("archive_version") or ARCHIVE_VERSION),
        "request_key_sha256": str(record["request_key_sha256"]),
        "path": str(record.get("path") or ""),
        "normalized_params": record.get("normalized_params") or [],
        "fetched_at_utc": str(record["fetched_at_utc"]),
        "payload_sha256": str(record["payload_sha256"]),
        "blob_key": str(record["blob_key"]),
        "observation_key": str(record["observation_key"]),
    }


def run(client=None):
    cfg = s3_config_from_env()
    if cfg is None:
        raise RuntimeError("S3/R2 raw archive storage is not configured")
    client = client or _s3_client(cfg)

    keys = list(iter_observation_keys(client, cfg["bucket"], cfg["prefix"]))
    workers = max(1, int(os.getenv("PBK_RAW_ARCHIVE_INDEX_WORKERS", "24")))

    def read_record(key):
        try:
            body = client.get_object(Bucket=cfg["bucket"], Key=key)["Body"].read()
            return json.loads(body.decode("utf-8"))
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(read_record, keys))

    unreadable = sum(1 for record in records if record is None)
    latest, invalid = latest_by_request(record for record in records if record is not None)

    written = 0
    for request_hash, record in latest.items():
        payload = index_payload(record)
        key = _request_index_key(cfg, request_hash)
        body = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        client.put_object(
            Bucket=cfg["bucket"],
            Key=key,
            Body=body,
            ContentType="application/json",
            Metadata={
                "request-key-sha256": request_hash,
                "payload-sha256": payload["payload_sha256"],
                "archive-version": VERSION,
            },
        )
        written += 1

    report = {
        "version": VERSION,
        "run_at_utc": iso_now(),
        "status": "OK",
        "backend": "S3",
        "observation_keys_discovered": len(keys),
        "observation_records_read": len(records) - unreadable,
        "unreadable_observation_records": unreadable,
        "invalid_observation_records": invalid,
        "unique_request_keys": len(latest),
        "request_index_rows_written": written,
        "provider_calls": 0,
        "reads_payload_blobs": False,
        "archive_first_ready": unreadable == 0 and invalid == 0 and written == len(latest),
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    return report


def main():
    report = run()
    OPS.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "OK" or not report["archive_first_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
