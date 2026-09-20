#!/usr/bin/env python3
"""Read-only inventory of PBK raw API-Football observations in S3/R2.

This stage lists immutable observation metadata only. It never calls API-Football
and never reads payload blobs unless a future stage explicitly does so.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    try:
    from api_football_raw_archive import s3_config_from_env, _s3_client
except ModuleNotFoundError:
    from scripts.api_football_raw_archive import s3_config_from_env, _s3_client
except ModuleNotFoundError:
    from scripts.api_football_raw_archive import s3_config_from_env, _s3_client

OPS = Path(os.getenv("OPS_DIR", "ops"))
OUT = OPS / "stage80_raw_archive_inventory_last_run.json"
VERSION = "PBK_STAGE80_RAW_ARCHIVE_INVENTORY_V1"
TARGET_PATHS = {"/fixtures/lineups", "/injuries"}


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def params_dict(value) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in value or []:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        key, raw = item
        key = str(key)
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = raw
        if parsed is None:
            continue
        out[key] = str(parsed)
    return out


def iter_observation_keys(client, bucket: str, prefix: str):
    paginator = client.get_paginator("list_objects_v2")
    root = f"{prefix}/observations/"
    for page in paginator.paginate(Bucket=bucket, Prefix=root):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if key.endswith(".json"):
                yield key


def inventory(client=None) -> dict:
    cfg = s3_config_from_env()
    if cfg is None:
        raise RuntimeError("S3/R2 raw archive storage is not configured")
    client = client or _s3_client(cfg)

    endpoint_counts: Counter[str] = Counter()
    target_counts: Counter[str] = Counter()
    target_fixture_ids: dict[str, set[str]] = {path: set() for path in TARGET_PATHS}
    target_first_seen: dict[str, str | None] = {path: None for path in TARGET_PATHS}
    target_last_seen: dict[str, str | None] = {path: None for path in TARGET_PATHS}
    total = 0
    invalid = 0

    for key in iter_observation_keys(client, cfg["bucket"], cfg["prefix"]):
        try:
            body = client.get_object(Bucket=cfg["bucket"], Key=key)["Body"].read()
            record = json.loads(body.decode("utf-8"))
        except Exception:
            invalid += 1
            continue

        total += 1
        path = str(record.get("path") or "")
        endpoint_counts[path] += 1
        if path not in TARGET_PATHS:
            continue

        target_counts[path] += 1
        params = params_dict(record.get("normalized_params"))
        fixture = params.get("fixture")
        if fixture:
            target_fixture_ids[path].add(fixture)

        fetched = str(record.get("fetched_at_utc") or "")
        if fetched:
            if target_first_seen[path] is None or fetched < target_first_seen[path]:
                target_first_seen[path] = fetched
            if target_last_seen[path] is None or fetched > target_last_seen[path]:
                target_last_seen[path] = fetched

    report = {
        "version": VERSION,
        "run_at_utc": iso_now(),
        "status": "OK",
        "backend": "S3",
        "bucket": cfg["bucket"],
        "prefix": cfg["prefix"],
        "observation_records": total,
        "invalid_observation_records": invalid,
        "endpoint_counts": dict(sorted(endpoint_counts.items())),
        "targets": {
            path: {
                "observations": target_counts[path],
                "unique_fixture_ids": len(target_fixture_ids[path]),
                "first_seen_utc": target_first_seen[path],
                "last_seen_utc": target_last_seen[path],
            }
            for path in sorted(TARGET_PATHS)
        },
        "reads_payload_blobs": False,
        "provider_calls": 0,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    return report


def main() -> None:
    report = inventory()
    OPS.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
