#!/usr/bin/env python3
"""PBK34 R2-only analysis of recovered match card events."""
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_football_broker import request_key
from api_football_raw_archive import read_archived_response, s3_config_from_env

ROOT = Path.cwd()
OUT = ROOT / "ops/pbk34_card_processing_380"
OUT.mkdir(parents=True, exist_ok=True)

scope = json.loads(os.environ["PBK34_PILOT_FIXTURE_IDS"])
if not isinstance(scope, list) or len(scope) != 1917:
    raise RuntimeError("INVALID_SCOPE")

if s3_config_from_env() is None:
    raise RuntimeError("R2_NOT_CONFIGURED")

columns = [
    "fixture_id", "league_id", "r2_status",
    "event_count", "card_event_count",
    "yellow_event_count", "red_event_count",
    "second_yellow_event_count", "other_card_event_count",
    "events_with_missing_team", "card_details_json",
    "card_events_json", "card_semantics_status",
    "full_match_card_totals_verified",
    "predictive_authority", "betting_authority"
]

rows = []
states = Counter()
details_total = Counter()

for item in scope:
    fid, lid = map(str, item)
    row = {x: "" for x in columns}
    row.update({
        "fixture_id": fid,
        "league_id": lid,
        "r2_status": "UNKNOWN",
        "full_match_card_totals_verified": "NO",
        "predictive_authority": "NOT_AUTHORIZED",
        "betting_authority": "NOT_AUTHORIZED"
    })

    try:
        key = request_key("GET", "/fixtures/events", {"fixture": fid})
        payload = read_archived_response(key)

        if payload is None:
            row["r2_status"] = "R2_MISSING"
            row["card_semantics_status"] = "NO_ARCHIVE"

        elif (
            not isinstance(payload, dict)
            or payload.get("errors")
            or not isinstance(payload.get("response"), list)
        ):
            row["r2_status"] = "R2_INVALID"
            row["card_semantics_status"] = "BAD_PAYLOAD"

        else:
            events = payload["response"]
            cards = []
            details = Counter()
            missing_team = 0

            for event in events:
                if not isinstance(event, dict):
                    raise RuntimeError("NON_OBJECT_EVENT")

                if str(event.get("type") or "").casefold() != "card":
                    continue

                detail = str(event.get("detail") or "").strip()
                details[detail or "UNSPECIFIED"] += 1

                team = event.get("team")
                tid = team.get("id") if isinstance(team, dict) else None
                if tid is None:
                    missing_team += 1

                player = event.get("player")
                time = event.get("time")

                cards.append({
                    "team_id": tid,
                    "player_id": (
                        player.get("id")
                        if isinstance(player, dict) else None
                    ),
                    "minute": (
                        time.get("elapsed")
                        if isinstance(time, dict) else None
                    ),
                    "detail": detail,
                    "comments": event.get("comments")
                })

            yellow = details.get("Yellow Card", 0)
            red = details.get("Red Card", 0)
            second = sum(
                n for name, n in details.items()
                if "second yellow" in name.casefold()
                or "2nd yellow" in name.casefold()
            )
            other = len(cards) - yellow - red - second

            if other < 0:
                raise RuntimeError("CARD_TYPE_OVERLAP")

            row.update({
                "r2_status": "R2_READ_VERIFIED",
                "event_count": len(events),
                "card_event_count": len(cards),
                "yellow_event_count": yellow,
                "red_event_count": red,
                "second_yellow_event_count": second,
                "other_card_event_count": other,
                "events_with_missing_team": missing_team,
                "card_details_json": json.dumps(
                    dict(details), ensure_ascii=False
                ),
                "card_events_json": json.dumps(
                    cards, ensure_ascii=False,
                    separators=(",", ":")
                ),
                "card_semantics_status": (
                    "EMPTY_EVENT_LIST_REVIEW" if not events else
                    "NO_CARD_EVENTS_UNVERIFIED_ZERO" if not cards else
                    "UNKNOWN_CARD_TYPE_REVIEW" if other else
                    "SECOND_YELLOW_REVIEW" if second else
                    "EVENT_COUNTS_ONLY_NOT_MATCH_TOTALS"
                )
            })
            details_total.update(details)

    except Exception as exc:
        row["r2_status"] = "R2_READ_ERROR"
        row["card_semantics_status"] = (
            type(exc).__name__ + ": " + str(exc)[:100]
        )

    states[row["r2_status"]] += 1
    rows.append(row)

    if len(rows) % 100 == 0:
        print("PROCESSED =", len(rows), "/", len(scope), flush=True)

csv_path = OUT / "pbk34_r2_card_events_380.csv"
json_path = OUT / "pbk34_r2_card_processing_380.json"

with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=columns)
    w.writeheader()
    w.writerows(rows)

summary = {
    "scope": len(scope),
    "r2_verified": states["R2_READ_VERIFIED"],
    "r2_missing": states["R2_MISSING"],
    "r2_invalid": states["R2_INVALID"],
    "r2_errors": states["R2_READ_ERROR"],
    "fixtures_with_card_events": sum(
        bool(r["card_event_count"])
        and int(r["card_event_count"]) > 0
        for r in rows
    ),
    "yellow_events": sum(int(r["yellow_event_count"] or 0) for r in rows),
    "red_events": sum(int(r["red_event_count"] or 0) for r in rows),
    "second_yellow_events": sum(
        int(r["second_yellow_event_count"] or 0) for r in rows
    ),
    "card_details": dict(details_total),
    "semantics_statuses": dict(Counter(
        r["card_semantics_status"] for r in rows
    )),
    "full_totals_authorized": False,
    "canonical_modified": False,
    "api_calls": 0
}

json_path.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

for k, v in summary.items():
    print(k.upper(), "=", v)

print("RESULT CSV =", csv_path)
print("RESULT JSON =", json_path)

if (
    states["R2_MISSING"]
    or states["R2_INVALID"]
    or states["R2_READ_ERROR"]
):
    raise SystemExit(2)
