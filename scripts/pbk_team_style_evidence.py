#!/usr/bin/env python3
"""PBK Team Style Evidence pipeline.

Provider-free adapter from the existing Stage80 raw API-Football archive into an
append-only team-level evidence ledger consumed by pbk_team_style_profiles.

The adapter never performs network I/O. It preserves provider observation time,
requires explicit fixture metadata to establish kickoff and home/away venue, and
never fills missing statistics with zero.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

EVIDENCE_VERSION = "PBK_TEAM_STYLE_EVIDENCE_V1"
FIXTURE_PATH = "/fixtures"
STATISTICS_PATH = "/fixtures/statistics"

STAT_MAP = {
    "Shots on Goal": "shots_on_target_for",
    "Total Shots": "shots_for",
    "Ball Possession": "possession_pct",
    "Corner Kicks": "corners_for",
    "Total passes": "passes",
    "Passes accurate %": "pass_accuracy_pct",
    "expected_goals": "xg_for",
    "Expected Goals": "xg_for",
}


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.endswith("%"):
            value = value[:-1].strip()
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _params_dict(record: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in record.get("normalized_params") or []:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            out[str(pair[0])] = str(pair[1])
    return out


def read_manifest(root: Path) -> list[dict[str, Any]]:
    path = root / "manifest.jsonl"
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for raw in stream:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def load_payload(root: Path, record: dict[str, Any]) -> dict[str, Any] | None:
    relative = record.get("blob_path")
    if not relative:
        return None
    path = root / str(relative)
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def build_fixture_index(root: Path, manifest: Iterable[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Return explicit fixture metadata observed in archived /fixtures payloads.

    If a fixture appears repeatedly, keep the newest valid provider observation.
    """
    index: dict[int, dict[str, Any]] = {}
    for record in manifest:
        if record.get("path") != FIXTURE_PATH:
            continue
        observed = parse_iso(record.get("fetched_at_utc"))
        if observed is None:
            continue
        payload = load_payload(root, record)
        if not payload:
            continue
        for item in payload.get("response") or []:
            if not isinstance(item, dict):
                continue
            fixture = item.get("fixture") or {}
            teams = item.get("teams") or {}
            fixture_id = fixture.get("id")
            kickoff = parse_iso(fixture.get("date"))
            home = teams.get("home") or {}
            away = teams.get("away") or {}
            if fixture_id is None or kickoff is None or home.get("id") is None or away.get("id") is None:
                continue
            row = {
                "fixture_id": int(fixture_id),
                "kickoff_utc": kickoff.isoformat(),
                "home_team_id": int(home["id"]),
                "home_team_name": home.get("name"),
                "away_team_id": int(away["id"]),
                "away_team_name": away.get("name"),
                "fixture_observed_at_utc": observed.isoformat(),
                "fixture_source_observation_id": record.get("observation_id"),
            }
            previous = index.get(int(fixture_id))
            if previous is None or observed > parse_iso(previous["fixture_observed_at_utc"]):
                index[int(fixture_id)] = row
    return index


def _extract_team_metrics(stats: Iterable[dict[str, Any]]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for row in stats or []:
        if not isinstance(row, dict):
            continue
        metric = STAT_MAP.get(str(row.get("type") or ""))
        if not metric:
            continue
        value = _number(row.get("value"))
        if value is not None:
            metrics[metric] = value
    return metrics


def evidence_from_statistics_observation(
    record: dict[str, Any], payload: dict[str, Any], fixture_index: dict[int, dict[str, Any]]
) -> tuple[list[dict[str, Any]], str | None]:
    """Convert one archived /fixtures/statistics observation into team rows."""
    observed = parse_iso(record.get("fetched_at_utc"))
    if observed is None:
        return [], "MISSING_AWARE_OBSERVED_AT"
    params = _params_dict(record)
    raw_fixture_id = params.get("fixture")
    try:
        fixture_id = int(raw_fixture_id) if raw_fixture_id is not None else None
    except (TypeError, ValueError):
        fixture_id = None
    if fixture_id is None:
        return [], "MISSING_FIXTURE_PARAM"
    fixture = fixture_index.get(fixture_id)
    if not fixture:
        return [], "MISSING_FIXTURE_METADATA"

    kickoff = parse_iso(fixture.get("kickoff_utc"))
    if kickoff is None:
        return [], "MISSING_FIXTURE_KICKOFF"

    rows: list[dict[str, Any]] = []
    for item in payload.get("response") or []:
        if not isinstance(item, dict):
            continue
        team = item.get("team") or {}
        team_id = team.get("id")
        if team_id is None:
            continue
        team_id = int(team_id)
        if team_id == fixture["home_team_id"]:
            venue = "HOME"
            opponent_id = fixture["away_team_id"]
            opponent_name = fixture["away_team_name"]
        elif team_id == fixture["away_team_id"]:
            venue = "AWAY"
            opponent_id = fixture["home_team_id"]
            opponent_name = fixture["home_team_name"]
        else:
            continue
        metrics = _extract_team_metrics(item.get("statistics") or [])
        rows.append({
            "schema_version": EVIDENCE_VERSION,
            "source": "API_FOOTBALL_RAW_ARCHIVE",
            "source_observation_id": record.get("observation_id"),
            "source_payload_sha256": record.get("payload_sha256"),
            "fixture_source_observation_id": fixture.get("fixture_source_observation_id"),
            "fixture_id": fixture_id,
            "kickoff_utc": kickoff.isoformat(),
            "observed_at_utc": observed.isoformat(),
            "team_id": team_id,
            "team_name": team.get("name"),
            "opponent_team_id": opponent_id,
            "opponent_team_name": opponent_name,
            "venue": venue,
            "metrics": metrics,
            "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
            "provider_calls_added": 0,
            "research_only": True,
            "creates_signal": False,
            "probability_mutation": False,
            "stake_changes": False,
        })
    return rows, None if rows else "NO_TEAM_STAT_ROWS"


def extract_archive_evidence(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = read_manifest(root)
    fixture_index = build_fixture_index(root, manifest)
    rows: list[dict[str, Any]] = []
    stats_observations = 0
    exclusions: dict[str, int] = {}
    for record in manifest:
        if record.get("path") != STATISTICS_PATH:
            continue
        stats_observations += 1
        payload = load_payload(root, record)
        if payload is None:
            exclusions["MISSING_PAYLOAD_BLOB"] = exclusions.get("MISSING_PAYLOAD_BLOB", 0) + 1
            continue
        converted, reason = evidence_from_statistics_observation(record, payload, fixture_index)
        if reason:
            exclusions[reason] = exclusions.get(reason, 0) + 1
        rows.extend(converted)
    return rows, {
        "status": "OK" if manifest else "ARCHIVE_UNAVAILABLE_OR_EMPTY",
        "archive_manifest_rows": len(manifest),
        "fixture_index_rows": len(fixture_index),
        "statistics_observations": stats_observations,
        "evidence_rows_extracted": len(rows),
        "exclusions": exclusions,
        "provider_calls_added": 0,
    }


def _dedupe_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (
        str(row.get("source_observation_id") or ""),
        int(row.get("fixture_id")),
        int(row.get("team_id")),
    )


def append_evidence(rows: Iterable[dict[str, Any]], out_path: Path) -> dict[str, int]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing: set[tuple[str, int, int]] = set()
    if out_path.exists():
        with out_path.open(encoding="utf-8") as stream:
            for raw in stream:
                try:
                    item = json.loads(raw)
                    existing.add(_dedupe_key(item))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
    added = 0
    skipped = 0
    with out_path.open("a", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            key = _dedupe_key(row)
            if key in existing:
                skipped += 1
                continue
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            existing.add(key)
            added += 1
    return {"rows_added": added, "duplicates_skipped": skipped, "ledger_rows_known": len(existing)}


def normalized_import_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Validate a provider-independent normalized historical row.

    This deliberately refuses to invent historical availability timestamps.
    Callers must supply aware kickoff_utc and observed_at_utc explicitly.
    """
    kickoff = parse_iso(row.get("kickoff_utc"))
    observed = parse_iso(row.get("observed_at_utc"))
    if kickoff is None or observed is None or row.get("team_id") is None or not row.get("venue"):
        return None
    venue = str(row.get("venue")).upper()
    if venue not in {"HOME", "AWAY"}:
        return None
    metrics = {}
    for key, value in (row.get("metrics") or {}).items():
        number = _number(value)
        if number is not None:
            metrics[str(key)] = number
    return {
        "schema_version": EVIDENCE_VERSION,
        "source": str(row.get("source") or "NORMALIZED_HISTORICAL_IMPORT"),
        "source_observation_id": str(row.get("source_observation_id") or ""),
        "source_payload_sha256": row.get("source_payload_sha256"),
        "fixture_id": int(row["fixture_id"]),
        "kickoff_utc": kickoff.isoformat(),
        "observed_at_utc": observed.isoformat(),
        "team_id": int(row["team_id"]),
        "team_name": row.get("team_name"),
        "opponent_team_id": int(row["opponent_team_id"]) if row.get("opponent_team_id") is not None else None,
        "opponent_team_name": row.get("opponent_team_name"),
        "venue": venue,
        "metrics": metrics,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "provider_calls_added": 0,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "stake_changes": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-dir", default=os.getenv("API_FOOTBALL_ARCHIVE_DIR", ""))
    parser.add_argument("--out", default=os.getenv("PBK_TEAM_STYLE_EVIDENCE_PATH", "ops/team_style_evidence.jsonl"))
    parser.add_argument("--meta", default="ops/team_style_evidence_last_run.json")
    args = parser.parse_args()

    root = Path(args.archive_dir) if args.archive_dir else None
    if root is None:
        extraction = {
            "status": "ARCHIVE_DIR_NOT_CONFIGURED",
            "archive_manifest_rows": 0,
            "fixture_index_rows": 0,
            "statistics_observations": 0,
            "evidence_rows_extracted": 0,
            "exclusions": {},
            "provider_calls_added": 0,
        }
        write_stats = {"rows_added": 0, "duplicates_skipped": 0, "ledger_rows_known": 0}
    else:
        rows, extraction = extract_archive_evidence(root)
        write_stats = append_evidence(rows, Path(args.out))

    meta = {
        "version": EVIDENCE_VERSION,
        "source_mode": "EXISTING_RAW_ARCHIVE_ONLY",
        "extraction": extraction,
        "ledger": write_stats,
        "provider_calls_added": 0,
        "style_scores_created": 0,
        "signals_created": 0,
        "probability_mutation": False,
        "stake_changes": False,
    }
    meta_path = Path(args.meta)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
