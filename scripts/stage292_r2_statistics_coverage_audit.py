#!/usr/bin/env python3
"""PBK Stage292 — provider-free R2 coverage audit for historical team statistics.

Checks exact /fixtures/statistics request-index presence for pending historical
Stage292 fixtures without downloading payload blobs and without API-Football.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from api_football_broker import request_key
from api_football_raw_archive import s3_config_from_env, _s3_client, _request_index_key, _not_found

OPS = Path(os.getenv("OPS_DIR", "ops"))
BACKLOG = OPS / "stage81_team_stats_backlog.csv"
OUT = OPS / "stage292_r2_statistics_coverage_audit.json"
WORKERS = int(os.getenv("STAGE292_R2_COVERAGE_WORKERS", "64"))


def read_csv(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def pending_historical(rows):
    out = []
    seen = set()
    for row in rows:
        fixture_id = str(row.get("fixture_id") or "").strip()
        if not fixture_id or fixture_id in seen:
            continue
        if str(row.get("backlog_status") or "").strip().upper() != "PENDING":
            continue
        if str(row.get("round") or "").strip().upper() != "HISTORICAL_BRIDGE":
            continue
        seen.add(fixture_id)
        out.append(row)
    return out


def request_index_key_for_fixture(config, fixture_id):
    key = request_key("GET", "/fixtures/statistics", {"fixture": fixture_id})
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return _request_index_key(config, digest)


def audit_fixture(client, config, row):
    fixture_id = str(row.get("fixture_id") or "").strip()
    index_key = request_index_key_for_fixture(config, fixture_id)
    try:
        client.head_object(Bucket=config["bucket"], Key=index_key)
        status = "HIT"
    except Exception as exc:
        if _not_found(exc):
            status = "MISS"
        else:
            return {**row, "coverage_status": "ERROR", "error": str(exc)}
    return {**row, "coverage_status": status, "error": ""}


def summarize(rows):
    overall = {"HIT": 0, "MISS": 0, "ERROR": 0}
    by_season = defaultdict(lambda: {"HIT": 0, "MISS": 0, "ERROR": 0})
    by_league = defaultdict(lambda: {"HIT": 0, "MISS": 0, "ERROR": 0})
    by_league_season = defaultdict(lambda: {"HIT": 0, "MISS": 0, "ERROR": 0})

    for row in rows:
        status = row["coverage_status"]
        overall[status] += 1
        season = str(row.get("season") or "UNKNOWN").strip() or "UNKNOWN"
        league = str(row.get("league_name") or "UNKNOWN").strip() or "UNKNOWN"
        by_season[season][status] += 1
        by_league[league][status] += 1
        by_league_season[f"{league}|{season}"][status] += 1

    def add_rate(mapping):
        out = {}
        for key, counts in sorted(mapping.items()):
            total = sum(counts.values())
            out[key] = {
                **counts,
                "total": total,
                "hit_rate_pct": round(100.0 * counts["HIT"] / total, 4) if total else 0.0,
            }
        return out

    total = sum(overall.values())
    return {
        "overall": {
            **overall,
            "total": total,
            "hit_rate_pct": round(100.0 * overall["HIT"] / total, 4) if total else 0.0,
        },
        "by_season": add_rate(by_season),
        "by_league": add_rate(by_league),
        "by_league_season": add_rate(by_league_season),
    }


def main():
    config = s3_config_from_env()
    if config is None:
        raise RuntimeError("R2 raw archive is not configured")

    backlog = read_csv(BACKLOG)
    pending = pending_historical(backlog)
    client = _s3_client(config)

    checked = []
    with ThreadPoolExecutor(max_workers=max(1, WORKERS)) as pool:
        futures = [pool.submit(audit_fixture, client, config, row) for row in pending]
        for future in as_completed(futures):
            checked.append(future.result())

    summary = summarize(checked)
    report = {
        "version": "PBK_STAGE292_R2_STATISTICS_COVERAGE_AUDIT_V1",
        "run_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "OK" if summary["overall"]["ERROR"] == 0 else "ATTENTION",
        "endpoint": "/fixtures/statistics",
        "pending_historical_fixtures": len(pending),
        "workers": WORKERS,
        "provider_calls": 0,
        "downloads_payload_blobs": False,
        "request_index_only": True,
        **summary,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
