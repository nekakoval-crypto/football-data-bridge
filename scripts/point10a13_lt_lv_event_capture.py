#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))

from api_football_broker import api_get, get_broker


OPS = ROOT / "ops"
OUT = OPS / "point10a13_lt_lv_event_capture_last_run.json"

TARGETS = [
    "1515889",
    "1515890",
    "1515891",
    "1515892",
    "1515893",
    "1515894",
    "1515895",
    "1515896",
    "1515898",
    "1547599",
    "1547600",
    "1547602",
    "1547603",
]


def main() -> int:

    if len(TARGETS) != 13:
        raise RuntimeError("Expected exactly 13 fixture IDs")

    if len(set(TARGETS)) != 13:
        raise RuntimeError("Duplicate fixture IDs detected")

    if not os.getenv("API_FOOTBALL_KEY", "").strip():
        raise RuntimeError("API_FOOTBALL_KEY missing")

    results = []

    for index, fixture_id in enumerate(TARGETS, start=1):

        print(
            f"[{index:02d}/13] fixture={fixture_id}",
            flush=True,
        )

        try:
            payload = api_get(
                "/fixtures/events",
                {"fixture": fixture_id},
                ttl_seconds=30 * 24 * 3600,
                force_refresh=False,
                archive_first=True,
                quota_class="HISTORICAL",
            )

        except Exception as exc:

            results.append(
                {
                    "fixture_id": fixture_id,
                    "status": "ERROR",
                    "error": repr(exc),
                }
            )

            print(
                f"    ERROR {exc!r}",
                flush=True,
            )

            continue

        response = []

        if isinstance(payload, dict):
            response = payload.get("response") or []

        if response:

            cards = [
                item
                for item in response
                if str(item.get("type") or "").lower() == "card"
            ]

            yellow = sum(
                str(item.get("detail") or "").lower()
                == "yellow card"
                for item in cards
            )

            red = sum(
                "red card"
                in str(item.get("detail") or "").lower()
                for item in cards
            )

            results.append(
                {
                    "fixture_id": fixture_id,
                    "status": "CAPTURED",
                    "event_rows": len(response),
                    "card_rows": len(cards),
                    "yellow_rows": yellow,
                    "red_rows": red,
                }
            )

            print(
                f"    CAPTURED events={len(response)} "
                f"cards={len(cards)} "
                f"yellow={yellow} "
                f"red={red}",
                flush=True,
            )

        else:

            results.append(
                {
                    "fixture_id": fixture_id,
                    "status": "NO_DATA",
                    "event_rows": 0,
                    "card_rows": 0,
                }
            )

            print(
                "    NO_DATA",
                flush=True,
            )

    stats = get_broker().stats()

    report = {
        "version": "PBK_POINT10A13_LT_LV_EVENT_CAPTURE_V1",
        "run_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),

        "target_fixtures": len(TARGETS),

        "captured": sum(
            r["status"] == "CAPTURED"
            for r in results
        ),

        "no_data": sum(
            r["status"] == "NO_DATA"
            for r in results
        ),

        "errors": sum(
            r["status"] == "ERROR"
            for r in results
        ),

        "real_api_calls": stats.get(
            "real_api_calls",
            0,
        ),

        "provider_successes": stats.get(
            "provider_successes",
            0,
        ),

        "archive_write_successes": stats.get(
            "archive_write_successes",
            0,
        ),

        "archive_errors": stats.get(
            "archive_errors",
            0,
        ),

        "archive_read_hits": stats.get(
            "archive_read_hits",
            0,
        ),

        "archive_read_misses": stats.get(
            "archive_read_misses",
            0,
        ),

        "global_quota_last_state": stats.get(
            "global_quota_last_state",
        ),

        "results": results,
    }

    OPS.mkdir(
        parents=True,
        exist_ok=True,
    )

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
    print("TARGET:", report["target_fixtures"])
    print("CAPTURED:", report["captured"])
    print("NO_DATA:", report["no_data"])
    print("ERRORS:", report["errors"])
    print("REAL API CALLS:", report["real_api_calls"])
    print("R2 WRITES:", report["archive_write_successes"])
    print("R2 WRITE ERRORS:", report["archive_errors"])
    print("=" * 80)

    if report["errors"]:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
