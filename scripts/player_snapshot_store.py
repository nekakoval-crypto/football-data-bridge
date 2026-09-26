#!/usr/bin/env python3
"""Partitioned PBK player snapshot store.

Large generated player ledgers outgrew GitHub's single-blob limit. This module
keeps the existing CSV schema but stores rows in deterministic year partitions.
Readers transparently support the legacy monolithic CSV during migration.

The authoritative row identity remains external to this module; callers may
merge/deduplicate after reading exactly as before.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

DEFAULT_UNKNOWN_PART = "unknown.csv"


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def snapshot_parts_dir(base_path: Path) -> Path:
    return base_path.with_name(base_path.stem + "_parts")


def read_snapshot_rows(base_path: Path, parts_dir: Path | None = None):
    """Read legacy monolith + deterministic partition files.

    During migration both may briefly exist. Callers that require uniqueness
    should keep their existing merge-by-identity logic.
    """
    parts_dir = parts_dir or snapshot_parts_dir(base_path)
    rows = []
    if base_path.exists():
        rows.extend(read_csv(base_path))
    if parts_dir.exists():
        for path in sorted(parts_dir.glob("*.csv")):
            rows.extend(read_csv(path))
    return rows


def partition_name(row) -> str:
    kickoff = str((row or {}).get("kickoff_utc") or "").strip()
    year = kickoff[:4]
    return f"{year}.csv" if len(year) == 4 and year.isdigit() else DEFAULT_UNKNOWN_PART


def write_csv_atomic(path: Path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def write_partitioned_rows(rows, parts_dir: Path, fields):
    grouped = defaultdict(list)
    for row in rows:
        grouped[partition_name(row)].append(dict(row))

    parts_dir.mkdir(parents=True, exist_ok=True)
    expected = set(grouped)
    for filename, bucket in grouped.items():
        write_csv_atomic(parts_dir / filename, fields, bucket)

    for stale in parts_dir.glob("*.csv"):
        if stale.name not in expected:
            stale.unlink()

    return {
        "partitions": len(grouped),
        "rows": sum(len(bucket) for bucket in grouped.values()),
        "files": sorted(grouped),
    }


def migrate_legacy_monolith(base_path: Path, parts_dir: Path, fields, rows):
    """Persist partitioned ledger and remove oversized legacy monolith."""
    result = write_partitioned_rows(rows, parts_dir, fields)
    if base_path.exists():
        base_path.unlink()
    return result
