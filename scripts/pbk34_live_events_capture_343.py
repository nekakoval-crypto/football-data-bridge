#!/usr/bin/env python3
"""PBK34 bounded provider capture with mandatory R2 read-back."""

import json
import os
import sys
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_football_broker import (
    ApiFootballBroker,
    ApiFootballBudgetExceeded,
    request_key,
)
from api_football_raw_archive import (
    read_archived_response,
    s3_config_from_env,
)

PILOT_FIXTURES = {
    "88": "1213444",
    "94": "1231736",
    "103": "1164320",
    "106": "1202950",
    "119": "1205424",
    "144": "1213202",
    "179": "1220119",
    "203": "1237851",
    "218": "1218574",
}

def resolve_fixture_scope():
    raw = os.getenv("PBK34_PILOT_FIXTURE_IDS", "").strip()

    if not raw:
        return list(PILOT_FIXTURES.items()), "LEGACY_PILOT"

    try:
        supplied = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("INVALID_FIXTURE_JSON") from exc

    if not isinstance(supplied, list):
        raise RuntimeError("FIXTURE_SCOPE_MUST_BE_ARRAY")

    if not 1 <= len(supplied) <= 2000:
        raise RuntimeError("FIXTURE_SCOPE_OUT_OF_RANGE")

    known = {
        fid: league
        for league, fid in PILOT_FIXTURES.items()
    }

    seen = set()
    resolved = []

    for item in supplied:
        if isinstance(item, dict):
            fid_value = item.get("fixture_id")
            league_value = item.get("provider_league_id")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            fid_value, league_value = item
        else:
            fid_value = item
            league_value = None

        if isinstance(fid_value, bool):
            raise RuntimeError("BOOLEAN_FIXTURE_ID")

        fid = str(fid_value or "").strip()

        if (
            not fid.isascii()
            or not fid.isdecimal()
            or int(fid) <= 0
            or fid in seen
        ):
            raise RuntimeError("INVALID_OR_DUPLICATE_FIXTURE_ID")

        seen.add(fid)
        league = known.get(fid)

        if league_value is not None:
            supplied_league = str(league_value).strip()

            if (
                isinstance(league_value, bool)
                or not supplied_league.isascii()
                or not supplied_league.isdecimal()
                or int(supplied_league) <= 0
            ):
                raise RuntimeError("INVALID_LEAGUE_ID")

            if league and league != supplied_league:
                raise RuntimeError("PILOT_LEAGUE_CONFLICT")

            league = supplied_league

        resolved.append((league or "UNRESOLVED", fid))

    return resolved, "DYNAMIC_BATCH"


FIXTURES, SCOPE_MODE = resolve_fixture_scope()

raw_max = os.getenv("PBK34_MAX_REAL_CALLS", "4").strip()

if not raw_max.isascii() or not raw_max.isdecimal():
    raise RuntimeError("INVALID_MAX_REAL_CALLS")

MAX_REAL_CALLS = int(raw_max)

if not 1 <= MAX_REAL_CALLS <= 2000:
    raise RuntimeError("REAL_CALL_CAP_OUT_OF_RANGE")


OUT = Path("ops/pbk34_live_events_capture_343_result.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

if not FIXTURES:
    raise RuntimeError("EMPTY_CAPTURE_SCOPE")

if len({fid for _, fid in FIXTURES}) != len(FIXTURES):
    raise RuntimeError("DUPLICATE_CAPTURE_SCOPE")

if s3_config_from_env() is None:
    raise RuntimeError("R2_STORAGE_NOT_CONFIGURED")

if not os.getenv("API_FOOTBALL_KEY", "").strip():
    raise RuntimeError("API_FOOTBALL_KEY_MISSING")

broker = ApiFootballBroker(
    max_real_calls=MAX_REAL_CALLS,
    attempts=1,
    default_ttl_seconds=0,
)

rows = []
fatal = False
stopped_by_budget = False
stopped_after_error = False

def valid(payload):
    return (
        isinstance(payload, dict)
        and not payload.get("errors")
        and isinstance(payload.get("response"), list)
    )

for league, fid in FIXTURES:
    row = {
        "provider_league_id": league,
        "fixture_id": fid,
        "status": None,
        "event_count": None,
        "card_event_count": None,
        "card_details": {},
        "r2_verified": False,
    }

    if stopped_after_error:
        row["status"] = "DEFERRED_AFTER_ERROR"
        rows.append(row)
        continue

    key = request_key(
        "GET", "/fixtures/events", {"fixture": fid}
    )

    try:
        archived = read_archived_response(key)

        if archived is not None:
            if not valid(archived):
                row["status"] = "ARCHIVE_INVALID"
                fatal = True
                rows.append(row)
                continue

            payload = archived
            row["status"] = "ARCHIVE_HIT"

        else:
            if stopped_by_budget:
                row["status"] = "DEFERRED_BY_BUDGET"
                rows.append(row)
                continue

            payload = broker.get(
                "/fixtures/events",
                {"fixture": fid},
                ttl_seconds=0,
                force_refresh=False,
                archive_first=True,
            )

            if not valid(payload):
                row["status"] = "PROVIDER_INVALID"
                fatal = True
                rows.append(row)
                continue

            # Mandatory durable read-back.
            stored = read_archived_response(key)

            if not valid(stored):
                row["status"] = "R2_WRITE_NOT_VERIFIED"
                fatal = True
                rows.append(row)
                continue

            if stored != payload:
                row["status"] = "R2_PAYLOAD_MISMATCH"
                fatal = True
                rows.append(row)
                continue

            row["status"] = "CAPTURED_R2_VERIFIED"

        row["r2_verified"] = True

        events = payload["response"]
        cards = [
            event for event in events
            if isinstance(event, dict)
            and str(event.get("type") or "").lower() == "card"
        ]

        details = Counter(
            str(event.get("detail") or "UNSPECIFIED")
            for event in cards
        )

        row["event_count"] = len(events)
        row["card_event_count"] = len(cards)
        row["card_details"] = dict(details)

        # Empty event arrays are NOT proof of zero cards.
        row["card_total_authorized"] = False

    except ApiFootballBudgetExceeded as exc:
        row["status"] = "BUDGET_BLOCKED"
        row["error_type"] = type(exc).__name__
        stopped_by_budget = True
        # Expected partial completion; do not promote card totals.

    except Exception as exc:
        row["status"] = "CAPTURE_ERROR"
        row["error_type"] = type(exc).__name__
        row["error_message"] = str(exc)[:350]
        tb = traceback.extract_tb(exc.__traceback__)
        if tb:
            frame = tb[-1]
            row["error_location"] = (
                f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
            )
        print(
            "DIAGNOSTIC_ERROR =", row["error_type"],
            "| LOCATION =", row.get("error_location"),
            "| MESSAGE =", row["error_message"],
            flush=True,
        )
        stopped_after_error = True
        fatal = True

    rows.append(row)
    print(
        "FIXTURE", fid,
        "LEAGUE", league,
        "STATUS", row["status"],
        "EVENTS", row["event_count"],
        "CARDS", row["card_event_count"],
        flush=True,
    )

stats = broker.stats()
real_calls = int(stats.get("real_api_calls") or 0)

if real_calls > MAX_REAL_CALLS:
    raise RuntimeError("REAL_API_CALL_CAP_EXCEEDED")

counts = Counter(r["status"] for r in rows)

result = {
    "contract": "PBK34_LIVE_EVENTS_CAPTURE_343",
    "endpoint": "/fixtures/events",
    "fixtures": len(FIXTURES),
    "scope_mode": SCOPE_MODE,
    "max_real_calls": MAX_REAL_CALLS,
    "partial_by_budget": stopped_by_budget,
    "results": rows,
    "status_counts": dict(counts),
    "real_provider_calls": real_calls,
    "archive_read_hits": sum(
        r["status"] == "ARCHIVE_HIT" for r in rows
    ),
    "r2_verified_fixtures": sum(
        r["r2_verified"] for r in rows
    ),
    "archive_write_successes": stats.get(
        "archive_write_successes", 0
    ),
    "archive_write_failures": stats.get(
        "archive_errors", 0
    ),
    "card_totals_promoted": 0,
    "existing_referee_observations_modified": False,
    "predictive_authority": False,
    "betting_authority": False,
}

OUT.write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=" * 76)
print("PBK34 LIVE CAPTURE SUMMARY")
print("PROVIDER CALLS =", real_calls)
print("R2 VERIFIED =", result["r2_verified_fixtures"])
print("STATUS COUNTS =", dict(counts))
print("RESULT =", OUT)
print("CARD TOTALS PROMOTED = 0")
print("=" * 76)

if fatal:
    raise SystemExit(2)

# A partially completed batch is not a fatal error.

