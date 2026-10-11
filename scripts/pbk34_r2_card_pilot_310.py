"""PBK34 R2 archive-only card pilot. Never calls a provider."""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_football_broker import request_key
from api_football_raw_archive import read_archived_response, s3_config_from_env

ids = json.loads(os.environ["PBK34_PILOT_FIXTURE_IDS"])
if len(ids) != 12 or len(set(ids)) != 12:
    raise RuntimeError("INVALID_PILOT_FIXTURE_SCOPE")
if any(not str(x).isdigit() for x in ids):
    raise RuntimeError("INVALID_FIXTURE_ID")

if s3_config_from_env() is None:
    raise RuntimeError("R2_NOT_CONFIGURED_IN_GITHUB")

results = []
counts = Counter()

for fid in ids:
    for endpoint in ("/fixtures/statistics", "/fixtures/events"):
        record = {
            "fixture_id": fid,
            "endpoint": endpoint,
            "status": None,
            "response_items": None,
            "card_fields": [],
            "card_event_count": None,
        }
        try:
            key = request_key("GET", endpoint, {"fixture": str(fid)})
            payload = read_archived_response(key)
            if payload is None:
                record["status"] = "MISS"
            elif payload.get("errors") or not isinstance(payload.get("response"), list):
                record["status"] = "INVALID_PAYLOAD"
            else:
                response = payload["response"]
                record["status"] = "HIT"
                record["response_items"] = len(response)

                if endpoint.endswith("statistics"):
                    for team in response:
                        if not isinstance(team, dict):
                            continue
                        team_id = (team.get("team") or {}).get("id")
                        for stat in team.get("statistics") or []:
                            if not isinstance(stat, dict):
                                continue
                            label = str(stat.get("type") or "")
                            if any(s in label.lower() for s in ("yellow", "red", "card")):
                                record["card_fields"].append({
                                    "team_id": team_id,
                                    "type": label,
                                    "value": stat.get("value"),
                                })
                else:
                    record["card_event_count"] = sum(
                        1 for event in response
                        if isinstance(event, dict)
                        and "card" in str(event.get("type") or "").lower()
                    )
        except Exception as exc:
            record["status"] = "READ_ERROR"
            record["error_type"] = type(exc).__name__

        counts[record["status"]] += 1
        results.append(record)
        print(fid, endpoint, record["status"])

output = {
    "contract": "PBK34_R2_CARD_PILOT_310",
    "fixtures": len(ids),
    "attempted_archive_reads": len(results),
    "counts": dict(counts),
    "results": results,
    "provider_api_calls": 0,
    "full_card_totals_authorized": 0,
    "betting_authority": False,
}

path = Path("ops/pbk34_r2_card_pilot_310_result.json")
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

print("SUMMARY =", dict(counts))
print("RESULT =", path)
if counts["READ_ERROR"]:
    raise SystemExit(2)
