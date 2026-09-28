#!/usr/bin/env python3
"""PBK Point 10.A.2 — exact R2 replay audit for LT/LV disciplinary backlog.

Provider-free by contract:
- reads exact /fixtures/players request keys from PBK raw archive;
- does not accept/use API_FOOTBALL_KEY;
- does not fall back to provider;
- does not mutate player stats or disciplinary state.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))

from api_football_broker import request_key, read_archived_response


OPS = ROOT / "ops"
BACKLOG = OPS / "disciplinary_current_season_finished_fixture_backlog.csv"
OUT = OPS / "disciplinary_lt_lv_r2_replay_audit_last_run.json"

VERSION = "PBK_POINT10A2_LT_LV_R2_REPLAY_AUDIT_V1"


def main() -> int:
    if os.getenv("API_FOOTBALL_KEY", "").strip():
        raise RuntimeError(
            "Provider-free contract violation: API_FOOTBALL_KEY must not be present"
        )

    required = [
        "PBK_RAW_ARCHIVE_S3_ACCESS_KEY_ID",
        "PBK_RAW_ARCHIVE_S3_SECRET_ACCESS_KEY",
        "PBK_RAW_ARCHIVE_S3_ENDPOINT",
        "PBK_RAW_ARCHIVE_S3_BUCKET",
    ]

    missing_env = [
        name for name in required
        if not os.getenv(name, "").strip()
    ]

    if missing_env:
        raise RuntimeError(
            "Missing R2 configuration: " + ", ".join(missing_env)
        )

    with BACKLOG.open(
        "r",
        encoding="utf-8-sig",
        newline="",
        errors="replace",
    ) as f:
        rows = list(csv.DictReader(f))

    targets = [
        row for row in rows
        if str(row.get("provider_league_id") or "").strip()
        in {"362", "365"}
    ]

    if len(targets) != 24:
        raise RuntimeError(
            f"Expected exactly 24 LT/LV backlog fixtures, got {len(targets)}"
        )

    hits = []
    misses = []
    errors = []

    for idx, row in enumerate(targets, start=1):
        fixture_id = str(row["fixture_id"]).strip()

        key = request_key(
            "GET",
            "/fixtures/players",
            {"fixture": fixture_id},
        )

        try:
            payload = read_archived_response(key)
        except Exception as exc:
            errors.append({
                "fixture_id": fixture_id,
                "error": repr(exc),
            })
            print(
                f"[{idx:02d}/24] ERROR {fixture_id}: {exc!r}",
                flush=True,
            )
            continue

        valid = (
            isinstance(payload, dict)
            and not payload.get("errors")
            and isinstance(payload.get("response"), list)
            and len(payload.get("response") or []) > 0
        )

        if valid:
            entry_count = len(payload["response"])

            hits.append({
                "fixture_id": fixture_id,
                "provider_league_id": row["provider_league_id"],
                "league_name": row["league_name"],
                "entries": entry_count,
            })

            print(
                f"[{idx:02d}/24] R2 HIT  "
                f"{fixture_id} entries={entry_count}",
                flush=True,
            )
        else:
            misses.append({
                "fixture_id": fixture_id,
                "provider_league_id": row["provider_league_id"],
                "league_name": row["league_name"],
            })

            print(
                f"[{idx:02d}/24] R2 MISS {fixture_id}",
                flush=True,
            )

    report = {
        "version": VERSION,
        "run_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "backlog_fixtures": len(targets),
        "r2_exact_replay_hits": len(hits),
        "r2_exact_replay_misses": len(misses),
        "r2_read_errors": len(errors),
        "provider_calls": 0,
        "provider_fallback_allowed": False,
        "disciplinary_state_mutation": False,
        "player_stats_mutation": False,
        "hits": hits,
        "misses": misses,
        "errors": errors,
    }

    OPS.mkdir(parents=True, exist_ok=True)

    OUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 80)
    print("R2 EXACT REPLAY HITS:", len(hits))
    print("R2 EXACT REPLAY MISSES:", len(misses))
    print("R2 READ ERRORS:", len(errors))
    print("PROVIDER CALLS: 0")
    print("PROVIDER FALLBACK: FORBIDDEN")
    print("=" * 80)

    # R2 misses are valid audit results.
    # Only read/configuration errors fail the job.
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
