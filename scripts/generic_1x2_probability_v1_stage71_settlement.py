#!/usr/bin/env python3
"""Settle Generic 1X2 v1 from Stage71's already-fetched final-score overlay.

This adapter performs no provider calls. It consumes only exact FT rows already
written by Stage71 Live Snapshot and only settles fixtures that already have a
frozen Generic 1X2 prematch event. It never reconstructs missed prematch data.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path

try:
    import generic_1x2_probability_v1_forward as fwd
except ModuleNotFoundError:  # package import in unit tests
    from scripts import generic_1x2_probability_v1_forward as fwd

OPS = Path(os.getenv("OPS_DIR", "ops"))
OVERLAY = OPS / "live_fixture_overlay.csv"
META = OPS / "generic_1x2_v1_stage71_settlement_last_run.json"


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _score(value):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def result_from_score(home, away):
    home_score = _score(home)
    away_score = _score(away)
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return "H"
    if home_score < away_score:
        return "A"
    return "D"


def rows_from_overlay(overlay_rows, prematch_events, existing_settlements):
    """Create settlement inputs only for frozen Generic fixtures with exact FT."""
    frozen = {str(event.get("fixture_id") or "") for event in prematch_events}
    settled = {str(event.get("fixture_id") or "") for event in existing_settlements}
    rows = []
    diagnostics = Counter()

    for row in overlay_rows:
        fixture_id = str(row.get("fixture_id") or "").strip()
        if not fixture_id:
            diagnostics["missing_fixture_id"] += 1
            continue
        if fixture_id not in frozen:
            diagnostics["without_frozen_prematch"] += 1
            continue
        if fixture_id in settled:
            diagnostics["already_settled"] += 1
            continue
        if str(row.get("status") or "").strip().lower() != "finished":
            diagnostics["not_finished"] += 1
            continue
        if str(row.get("source_status") or "").strip().upper() != "FT":
            diagnostics["not_exact_ft"] += 1
            continue
        result = result_from_score(row.get("score_home"), row.get("score_away"))
        if result is None:
            diagnostics["missing_final_score"] += 1
            continue
        settled_at = str(row.get("observed_at_utc") or "").strip()
        if fwd.parse_iso(settled_at) is None:
            diagnostics["invalid_settlement_timestamp"] += 1
            continue
        rows.append({
            "fixture_id": fixture_id,
            "result": result,
            "settled_at_utc": settled_at,
        })

    diagnostics["eligible_settlement_rows"] = len(rows)
    return rows, dict(diagnostics)


def run(ops_dir=OPS, config_path=fwd.DEFAULT_CFG, overlay_path=None):
    ops_dir = Path(ops_dir)
    overlay_path = Path(overlay_path) if overlay_path is not None else ops_dir / "live_fixture_overlay.csv"
    cfg, _ = fwd.load_contract(config_path)
    prematch_path, settlement_path, report_path = fwd.output_paths(ops_dir, cfg)
    _, prematch = fwd.read_jsonl(prematch_path)
    settlement_raw, settlements = fwd.read_jsonl(settlement_path)

    candidates, extraction = rows_from_overlay(read_csv(overlay_path), prematch, settlements)
    added, rejected = fwd.settle_rows(candidates, prematch, settlements)
    fwd.atomic_append_jsonl(settlement_path, settlement_raw, added)
    settlements = settlements + added
    report = fwd.performance_report(cfg, prematch, settlements)
    fwd.atomic_write_json(report_path, report)

    payload = {
        "run_at_utc": fwd.now_iso(),
        "status": "OK",
        "mode": "STAGE71_EXISTING_OVERLAY_SETTLEMENT",
        "provider_calls_added": 0,
        "accepted_source_status": "FT_ONLY",
        "historical_backfill": "FORBIDDEN",
        "prematch_required": True,
        "extraction": extraction,
        "settlements_added": len(added),
        "settlements_rejected": len(rejected),
        "prematch_frozen": len(prematch),
        "settled_rows": len(settlements),
        "league_status_counts": report.get("league_status_counts", {}),
        "rejections": rejected,
    }
    fwd.atomic_write_json(ops_dir / META.name, payload)
    print(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    return payload


def main():
    run()


if __name__ == "__main__":
    main()
