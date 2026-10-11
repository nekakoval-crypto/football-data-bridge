
"""PBK34 batch archive reader: statistics only, zero provider calls."""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_football_broker import request_key
from api_football_raw_archive import (
    read_archived_response, s3_config_from_env
)

ids = json.loads(os.environ["PBK34_PILOT_FIXTURE_IDS"])

if not isinstance(ids, list) or not 1 <= len(ids) <= 180:
    raise RuntimeError("INVALID_BATCH_SIZE")

if len({str(x) for x in ids}) != len(ids):
    raise RuntimeError("DUPLICATE_IDS")

if any(not str(x).isdigit() for x in ids):
    raise RuntimeError("INVALID_ID")

if s3_config_from_env() is None:
    raise RuntimeError("R2_NOT_CONFIGURED")

results = []
counts = Counter()

for fid in ids:
    fid = str(fid)
    record = {
        "fixture_id": fid,
        "endpoint": "/fixtures/statistics",
        "status": None,
        "teams": [],
    }

    try:
        key = request_key(
            "GET", "/fixtures/statistics", {"fixture": fid}
        )
        payload = read_archived_response(key)

        if payload is None:
            record["status"] = "MISS"
        elif (
            not isinstance(payload, dict)
            or payload.get("errors")
            or not isinstance(payload.get("response"), list)
        ):
            record["status"] = "INVALID_PAYLOAD"
        else:
            response = payload["response"]

            for team in response:
                if not isinstance(team, dict):
                    continue

                stats = {}
                for item in team.get("statistics") or []:
                    if not isinstance(item, dict):
                        continue

                    label = str(item.get("type") or "").lower()
                    if label in ("yellow cards", "red cards"):
                        stats[label] = item.get("value")

                record["teams"].append({
                    "team_id": (team.get("team") or {}).get("id"),
                    "yellow_cards": stats.get("yellow cards"),
                    "red_cards": stats.get("red cards"),
                    "yellow_field_present": "yellow cards" in stats,
                    "red_field_present": "red cards" in stats,
                })

            record["status"] = "HIT"
            if len(record["teams"]) != 2:
                counts["HIT_WITHOUT_TWO_TEAMS"] += 1

    except Exception as exc:
        record["status"] = "READ_ERROR"
        record["error_type"] = type(exc).__name__

    counts[record["status"]] += 1
    results.append(record)

    print(fid, record["status"], flush=True)

out = {
    "contract": "PBK34_R2_CARD_BATCH_315",
    "requested_fixtures": len(ids),
    "archive_reads": len(results),
    "counts": dict(counts),
    "results": results,
    "provider_api_calls": 0,
    "card_totals_promoted": 0,
    "betting_authority": False,
}

destination = Path("ops/pbk34_r2_card_batch_315_result.json")
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(
    json.dumps(out, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("SUMMARY =", dict(counts))
print("REPORT =", destination)

if counts["READ_ERROR"]:
    raise SystemExit(2)
