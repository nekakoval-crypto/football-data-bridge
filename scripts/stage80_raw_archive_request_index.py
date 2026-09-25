#!/usr/bin/env python3
"""Backfill fast request-index pointers for existing PBK R2 raw observations.

Provider-free. Reads immutable observation metadata already stored in R2 and
writes one mutable request-index pointer per exact API-Football request key.
Payload blobs are not downloaded and API-Football is never called.

V2 throughput strategy:
- stream observation pages instead of materializing the full key list;
- read observation metadata concurrently and merge latest-per-request online;
- write request-index pointers concurrently;
- emit heartbeat progress so long R2 scans are visible in Actions.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
VERSION = "PBK_STAGE80_RAW_ARCHIVE_REQUEST_INDEX_V2"


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iter_observation_pages(client, bucket, prefix):
    paginator = client.get_paginator("list_objects_v2")
    root = f"{prefix}/observations/"
    for page in paginator.paginate(Bucket=bucket, Prefix=root):
        keys = []
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if key.endswith(".json"):
                keys.append(key)
        if keys:
            yield keys


def iter_observation_keys(client, bucket, prefix):
    for page in iter_observation_pages(client, bucket, prefix):
        yield from page


def valid_record(record):
    return (
        isinstance(record, dict)
        and bool(str(record.get("request_key_sha256") or ""))
        and bool(str(record.get("payload_sha256") or ""))
        and bool(str(record.get("blob_key") or ""))
        and bool(str(record.get("observation_key") or ""))
        and bool(str(record.get("fetched_at_utc") or ""))
    )


def merge_latest(latest, record):
    if not valid_record(record):
        return False
    request_hash = str(record["request_key_sha256"])
    current = latest.get(request_hash)
    if current is None or str(record["fetched_at_utc"]) > str(current["fetched_at_utc"]):
        latest[request_hash] = dict(record)
    return True


def latest_by_request(records):
    latest = {}
    invalid = 0
    for record in records:
        if not merge_latest(latest, record):
            invalid += 1
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

    read_workers = max(1, int(os.getenv("PBK_RAW_ARCHIVE_INDEX_READ_WORKERS", "64")))
    write_workers = max(1, int(os.getenv("PBK_RAW_ARCHIVE_INDEX_WRITE_WORKERS", "64")))
    heartbeat_pages = max(1, int(os.getenv("PBK_RAW_ARCHIVE_INDEX_HEARTBEAT_PAGES", "1")))
    heartbeat_writes = max(1, int(os.getenv("PBK_RAW_ARCHIVE_INDEX_HEARTBEAT_WRITES", "5000")))

    started = time.monotonic()
    latest = {}
    discovered = 0
    read_ok = 0
    unreadable = 0
    invalid = 0
    pages = 0

    def read_record(key):
        try:
            body = client.get_object(Bucket=cfg["bucket"], Key=key)["Body"].read()
            return json.loads(body.decode("utf-8"))
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=read_workers) as pool:
        for pages, keys in enumerate(iter_observation_pages(client, cfg["bucket"], cfg["prefix"]), start=1):
            discovered += len(keys)
            futures = [pool.submit(read_record, key) for key in keys]
            for future in as_completed(futures):
                record = future.result()
                if record is None:
                    unreadable += 1
                    continue
                read_ok += 1
                if not merge_latest(latest, record):
                    invalid += 1
            if pages % heartbeat_pages == 0:
                elapsed = max(0.001, time.monotonic() - started)
                print(
                    f"[read] pages={pages} discovered={discovered} read_ok={read_ok} "
                    f"unreadable={unreadable} invalid={invalid} unique_requests={len(latest)} "
                    f"rate={read_ok / elapsed:.1f}/s",
                    flush=True,
                )

    read_elapsed = time.monotonic() - started

    def write_index(item):
        request_hash, record = item
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
        return 1

    written = 0
    write_started = time.monotonic()
    with ThreadPoolExecutor(max_workers=write_workers) as pool:
        futures = [pool.submit(write_index, item) for item in latest.items()]
        for future in as_completed(futures):
            written += future.result()
            if written % heartbeat_writes == 0:
                elapsed = max(0.001, time.monotonic() - write_started)
                print(
                    f"[write] written={written}/{len(latest)} rate={written / elapsed:.1f}/s",
                    flush=True,
                )

    write_elapsed = time.monotonic() - write_started
    total_elapsed = time.monotonic() - started

    report = {
        "version": VERSION,
        "run_at_utc": iso_now(),
        "status": "OK",
        "backend": "S3",
        "observation_pages_scanned": pages,
        "observation_keys_discovered": discovered,
        "observation_records_read": read_ok,
        "unreadable_observation_records": unreadable,
        "invalid_observation_records": invalid,
        "unique_request_keys": len(latest),
        "request_index_rows_written": written,
        "read_workers": read_workers,
        "write_workers": write_workers,
        "read_elapsed_seconds": round(read_elapsed, 3),
        "write_elapsed_seconds": round(write_elapsed, 3),
        "total_elapsed_seconds": round(total_elapsed, 3),
        "provider_calls": 0,
        "reads_payload_blobs": False,
        "archive_first_ready": (
            unreadable == 0
            and invalid == 0
            and written == len(latest)
        ),
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
