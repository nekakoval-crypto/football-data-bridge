#!/usr/bin/env python3
"""Provider-free producer for the Stage77 finished-fixture backlog.

Stage71 owns the rolling provider-defined current-round observation. This helper
copies any terminal fixture already present in that persisted observation into
Stage77's durable backlog immediately after current-round capture, without making
any provider call. Stage77 remains the low-priority consumer that later fetches
`/fixtures/players` under its protected budget.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import stage77_player_stats_capture as stage77


def refresh(ops: Path, now=None):
    now = now or datetime.now(timezone.utc)
    fixtures = stage77.read_csv(ops / "current_round_fixtures.csv")
    stats = stage77.read_csv(ops / "player_stats_snapshots.csv")
    grades = stage77.read_csv(ops / "player_grade_snapshots.csv")
    existing = stage77.read_csv(ops / "stage77_player_stats_backlog.csv")

    result = stage77.sync_backlog(existing, fixtures, stats, grades, now)
    stage77.write_csv_atomic(
        ops / "stage77_player_stats_backlog.csv",
        stage77.BACKLOG_FIELDS,
        result["rows"],
    )
    return {
        "status": "OK",
        "provider_calls": 0,
        "current_round_rows": len(fixtures),
        "terminal_seen": result["terminal_seen"],
        "new_backlog_rows": result["new_rows"],
        "backlog_rows": len(result["rows"]),
        "pending": result["pending"],
        "captured": result["captured"],
    }


def main():
    ops = Path(os.getenv("OPS_DIR", "ops"))
    print(json.dumps(refresh(ops), ensure_ascii=False))


if __name__ == "__main__":
    main()
