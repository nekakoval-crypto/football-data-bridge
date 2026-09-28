#!/usr/bin/env python3
"""PBK Point 10.A.2 — exact R2 replay audit for LT/LV disciplinary backlog.

Provider-free by contract:
- exact fixed set of 24 already-audited LT/LV fixture IDs;
- reads only PBK R2 raw archive;
- no API_FOOTBALL_KEY;
- no provider fallback;
- no disciplinary/player-state mutation.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))

from api_football_broker import request_key, read_archived_response


OPS = ROOT / "ops"
OUT = OPS / "disciplinary_lt_lv_r2_replay_audit_last_run.json"

VERSION = "PBK_POINT10A2_LT_LV_R2_REPLAY_AUDIT_V2"


TARGETS = [
    # Virsliga — provider league 365
    {"fixture_id": "1515889", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515890", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515891", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515892", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515893", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515894", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515895", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515896", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515898", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515924", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515925", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515926", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515927", "provider_league_id": "365", "league_name": "Virsliga"},
    {"fixture_id": "1515928", "provider_league_id": "365", "league_name": "Virsliga"},

    # A Lyga — provider league 362
    {"fixture_id": "1547585", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547586", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547599", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547600", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547602", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547603", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547634", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547635", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547636", "provider_league_id": "362", "league_name": "A Lyga"},
    {"fixture_id": "1547637", "provider_league_id": "362", "league_name": "A Lyga"},
]


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
        name
        for name in required
        if not os.getenv(name, "").strip()
    ]

    if missing_env:
        raise RuntimeError(
            "Missing R2 configuration: " + ", ".join(missing_env)
        )

    if len(TARGETS) != 24:
        raise RuntimeError(
            f"Expected exactly 24 LT/LV targets, got {len(TARGETS)}"
        )

    fixture_ids = [row["fixture_id"] for row in TARGETS]

    if len(fixture_ids) != len(set(fixture_ids)):
        raise RuntimeError("Duplicate fixture IDs in fixed audit target set")

    hits = []
    misses = []
    errors = []

    for idx, row in enumerate(TARGETS, start=1):
        fixture_id = row["fixture_id"]

        key = request_key(
            "GET",
            "/fixtures/players",
            {"fixture": fixture_id},
        )

        try:
            payload = read_archived_response(key)
        except Exception as exc:
            errors.append(
                {
                    "fixture_id": fixture_id,
                    "error": repr(exc),
                }
            )

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
            entries = len(payload["response"])

            hits.append(
                {
                    **row,
                    "entries": entries,
                }
            )

            print(
                f"[{idx:02d}/24] R2 HIT  "
                f"{fixture_id} entries={entries}",
                flush=True,
            )

        else:
            misses.append(dict(row))

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
        "target_source": "FIXED_PREVIOUSLY_AUDITED_LT_LV_24",
        "backlog_fixtures": len(TARGETS),
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

    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
