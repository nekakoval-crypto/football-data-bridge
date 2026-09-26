from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["API_FOOTBALL_MAX_REAL_CALLS"] = "1"

from scripts.api_football_broker import get_broker


TEAM_ID = "33"
TEAM_NAME = "Manchester United"

OPS = Path("ops")
OUT = OPS / "point14_coach_real_provider_proof.json"


def sval(value):
    return str(value if value is not None else "").strip()


def real_calls(stats):
    return sum(
        int(value or 0)
        for value in (stats.get("real_calls_by_path") or {}).values()
    )


broker = get_broker()

before = broker.stats()
calls_before = real_calls(before)

print("=" * 100)
print("PBK POINT14 — REAL /coachs PROOF")
print("=" * 100)
print("team_id =", TEAM_ID)
print("team_name =", TEAM_NAME)
print("endpoint = /coachs")
print("archive_first = True")
print("hard_provider_call_cap = 1")
print("real_calls_before =", calls_before)

payload = broker.get(
    "/coachs",
    {"team": TEAM_ID},
    archive_first=True,
)

after = broker.stats()
calls_after = real_calls(after)

provider_calls = calls_after - calls_before

if provider_calls > 1:
    raise RuntimeError(
        f"Provider call cap violated: {provider_calls}"
    )

if not isinstance(payload, dict):
    raise RuntimeError("Provider payload is not a dict")

if payload.get("errors"):
    raise RuntimeError(
        f"Provider returned errors: {payload.get('errors')}"
    )

response = payload.get("response")

if not isinstance(response, list):
    raise RuntimeError(
        "Provider response is not a list"
    )

team_rows = []

for coach in response:

    if not isinstance(coach, dict):
        continue

    coach_id = sval(coach.get("id"))
    coach_name = sval(coach.get("name"))

    career = coach.get("career")

    if not isinstance(career, list):
        career = []

    for item in career:

        if not isinstance(item, dict):
            continue

        team = item.get("team")

        if not isinstance(team, dict):
            team = {}

        row = {
            "coach_id": coach_id,
            "coach_name": coach_name,
            "team_id": sval(team.get("id")),
            "team_name": sval(team.get("name")),
            "start": sval(item.get("start")),
            "end": sval(item.get("end")),
        }

        if row["team_id"] == TEAM_ID:
            team_rows.append(row)


result = {
    "version": "PBK_POINT14_COACH_PROVIDER_PROOF_V3",
    "team_id": TEAM_ID,
    "team_name": TEAM_NAME,
    "endpoint": "/coachs",
    "response_entries": len(response),
    "team_career_rows": team_rows,
    "provider_calls_this_proof": provider_calls,
    "archive_first": True,
    "archive_enabled": after.get("archive_enabled"),
    "archive_backend": after.get("archive_backend"),
    "archive_read_hits_delta": (
        int(after.get("archive_read_hits") or 0)
        - int(before.get("archive_read_hits") or 0)
    ),
    "archive_read_misses_delta": (
        int(after.get("archive_read_misses") or 0)
        - int(before.get("archive_read_misses") or 0)
    ),
    "archive_write_successes_delta": (
        int(after.get("archive_write_successes") or 0)
        - int(before.get("archive_write_successes") or 0)
    ),
    "coach_tenure_history_mutation": False,
    "automatic_promotion": False,
    "research_only": True,
}


OPS.mkdir(
    parents=True,
    exist_ok=True,
)

OUT.write_text(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ) + "\n",
    encoding="utf-8",
)


print()
print("=" * 100)
print("TEAM-33 CAREER ROWS")
print("=" * 100)

for row in team_rows:
    print(json.dumps(row, ensure_ascii=False))


print()
print("=" * 100)
print("PROOF SUMMARY")
print("=" * 100)

print(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )
)


if not team_rows:
    raise RuntimeError(
        "No Manchester United career rows returned"
    )


print()
print("REAL /COACHS PROOF PASSED")
