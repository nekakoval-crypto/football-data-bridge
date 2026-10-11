
"""PBK34 archive-only events pilot; no provider calls."""

import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_football_broker import request_key
from api_football_raw_archive import (
    read_archived_response,
    s3_config_from_env,
)

ids = json.loads(os.environ["PBK34_PILOT_FIXTURE_IDS"])

if len(ids) != 90 or len(set(map(str, ids))) != 90:
    raise RuntimeError("EXPECTED_90_FIXTURES")

if s3_config_from_env() is None:
    raise RuntimeError("R2_CONFIGURATION_MISSING")

results = []
counts = Counter()

for raw_id in ids:
    fid = str(raw_id)
    record = {
        "fixture_id": fid,
        "status": None,
        "event_count": None,
        "card_event_count": None,
        "card_events": [],
    }

    try:
        key = request_key(
            "GET", "/fixtures/events", {"fixture": fid}
        )
        response = read_archived_response(key)

        if response is None:
            record["status"] = "MISS"
        elif (
            not isinstance(response, dict)
            or response.get("errors")
            or not isinstance(response.get("response"), list)
        ):
            record["status"] = "INVALID_RESPONSE"
        else:
            events = response["response"]
            record["status"] = "HIT"
            record["event_count"] = len(events)

            for event in events:
                if not isinstance(event, dict):
                    continue

                if str(event.get("type") or "").lower() != "card":
                    continue

                record["card_events"].append({
                    "time": event.get("time"),
                    "team_id": (
                        (event.get("team") or {}).get("id")
                    ),
                    "player_id": (
                        (event.get("player") or {}).get("id")
                    ),
                    "detail": event.get("detail"),
                    "comments": event.get("comments"),
                })

            record["card_event_count"] = len(
                record["card_events"]
            )

    except Exception as exc:
        record["status"] = "READ_ERROR"
        record["error_type"] = type(exc).__name__

    counts[record["status"]] += 1
    results.append(record)
    print(
        fid,
        record["status"],
        "CARD_EVENTS =", record["card_event_count"],
        flush=True,
    )

output = {
    "contract": "PBK34_R2_EVENTS_PILOT_339",
    "requested_fixtures": len(ids),
    "results": results,
    "counts": dict(counts),
    "provider_api_calls": 0,
    "match_totals_promoted": 0,
    "betting_authority": False,
}

path = Path("ops/pbk34_r2_events_pilot_339_result.json")
path.write_text(
    json.dumps(output, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("SUMMARY =", dict(counts))
print("OUTPUT =", path)

if counts["READ_ERROR"]:
    raise SystemExit(2)
