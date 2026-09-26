#!/usr/bin/env python3
"""Real Stage77 recovery proof using the production raw archive.

The verifier never mutates committed ops data. It selects one fixture already
known as CAPTURED, confirms exact raw-archive replay is available, removes that
fixture from an in-memory copy of normalized ledgers, and proves Stage77 can
reconstruct it without calling provider/budget fallback.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import stage77_historical_player_backfill as h
import stage77_player_stats_capture as current
from api_football_broker import make_archive_before_budget_get, read_archived_response, request_key
from player_snapshot_store import read_snapshot_rows


OPS = Path("ops")


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    history = h.historical_fixture_map(read_csv(OPS / "pbk16_all_competition_fixture_history.csv"))
    state = h.read_state(read_csv(OPS / "stage77_historical_player_backfill_state.csv"))

    stats = current.merge_rows(
        [],
        read_snapshot_rows(OPS / "player_stats_snapshots.csv"),
    )
    grades = current.merge_rows(
        [],
        read_snapshot_rows(OPS / "player_grade_snapshots.csv"),
    )
    completed = h.completed_fixture_ids(stats, grades)

    selected = None
    archived_payload = None
    for fixture_id, row in state.items():
        if h.sval(row, "last_attempt_result").upper() != "CAPTURED":
            continue
        if fixture_id not in completed or fixture_id not in history:
            continue
        key = request_key("GET", "/fixtures/players", {"fixture": fixture_id})
        try:
            payload = read_archived_response(key)
        except Exception:
            continue
        if (
            isinstance(payload, dict)
            and not payload.get("errors")
            and isinstance(payload.get("response"), list)
            and payload.get("response")
        ):
            selected = history[fixture_id]
            archived_payload = payload
            break

    if selected is None:
        raise RuntimeError("No CAPTURED fixture with exact raw archive replay evidence found")

    fixture_id = h.sval(selected, "fixture_id")
    stats_without = [row for row in stats if h.sval(row, "fixture_id") != fixture_id]
    grades_without = [row for row in grades if h.sval(row, "fixture_id") != fixture_id]

    completed_without = h.completed_fixture_ids(stats_without, grades_without)
    if fixture_id in completed_without:
        raise RuntimeError("Fixture unexpectedly remains complete after simulated normalized loss")

    candidates = h.candidate_rows(
        {fixture_id: selected},
        captured=completed_without,
        state={fixture_id: state[fixture_id]},
        no_data_cell_threshold=8,
    )
    if [h.sval(row, "fixture_id") for row in candidates] != [fixture_id]:
        raise RuntimeError("CAPTURED state with missing normalized rows was not scheduled for replay")

    fallback_calls = []
    archive_stats = {
        "archive_read_hits": 0,
        "archive_read_misses": 0,
        "archive_read_errors": 0,
    }

    def forbidden_fallback(path, params=None, **kwargs):
        fallback_calls.append((path, dict(params or {})))
        raise AssertionError("provider/budget fallback must not be used in recovery proof")

    get = make_archive_before_budget_get(
        forbidden_fallback,
        archive_stats,
        require_archive_after_fallback=True,
    )

    replay_state = {fixture_id: dict(state[fixture_id])}
    result = h.run_capture(
        candidates,
        stats_without,
        grades_without,
        replay_state,
        get,
        datetime.now(timezone.utc),
        limit=1,
        no_data_cell_threshold=8,
    )

    recovered = h.completed_fixture_ids(result["stats"], result["grades"])
    proof = {
        "version": "PBK_STAGE77_REAL_RECOVERY_PROOF_V1",
        "status": "OK" if fixture_id in recovered and not fallback_calls else "FAIL",
        "fixture_id": fixture_id,
        "archive_response_entries": len(archived_payload.get("response") or []),
        "archive_read_hits": archive_stats["archive_read_hits"],
        "archive_read_misses": archive_stats["archive_read_misses"],
        "archive_read_errors": archive_stats["archive_read_errors"],
        "fallback_calls": len(fallback_calls),
        "captured_fixtures": result["captured_fixtures"],
        "new_stats_rows": result["new_stats_rows"],
        "new_grade_rows": result["new_grade_rows"],
        "recovered_complete": fixture_id in recovered,
        "provider_or_budget_used": bool(fallback_calls),
        "simulated_condition": "CAPTURED_STATE_WITH_NORMALIZED_STATS_AND_GRADES_REMOVED",
        "raw_archive_exact_replay": True,
        "mutates_repo_outputs": False,
    }

    print(json.dumps(proof, ensure_ascii=False, indent=2))
    if proof["status"] != "OK":
        raise RuntimeError("Stage77 real recovery proof failed")


if __name__ == "__main__":
    main()
