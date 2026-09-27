from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["API_FOOTBALL_MAX_REAL_CALLS"] = "2"

from scripts.api_football_broker import get_broker
from scripts.coach_tenure import (
    compare_candidate_to_verified,
    read_coach_tenures,
)


TARGETS = [
    ("47", "Tottenham"),
    ("496", "Juventus"),
]

OPS = Path("ops")
OUT = OPS / "point14_coach_provider_v17.json"


def sval(value):
    return str(value if value is not None else "").strip()


def real_calls(stats):
    return sum(
        int(value or 0)
        for value in (stats.get("real_calls_by_path") or {}).values()
    )


def extract_team_rows(payload, team_id):
    response = payload.get("response")
    if not isinstance(response, list):
        raise RuntimeError("Provider response is not a list")

    rows = []

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

            if row["team_id"] == team_id:
                rows.append(row)

    return rows


broker = get_broker()
verified = read_coach_tenures()

before = broker.stats()
calls_before = real_calls(before)

results = []

for team_id, team_name in TARGETS:
    payload = broker.get(
        "/coachs",
        {"team": team_id},
        archive_first=True,
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Provider payload for team {team_id} is not a dict"
        )

    if payload.get("errors"):
        raise RuntimeError(
            f"Provider returned errors for team {team_id}: "
            f"{payload.get('errors')}"
        )

    team_rows = extract_team_rows(
        payload,
        team_id,
    )

    if not team_rows:
        raise RuntimeError(
            f"No provider career rows returned for team {team_id}"
        )

    candidates = []

    for row in team_rows:
        candidate = {
            "team_id": row["team_id"],
            "team_name": row["team_name"],
            "coach_id": row["coach_id"],
            "coach_name": row["coach_name"],
            "valid_from_utc": row["start"],
            "valid_to_utc": row["end"],
            "effective_precision": "DATE",
            "source_type": "API_FOOTBALL_COACHS",
            "source_ref": f"/coachs?team={team_id}",
            "observed_at_utc": "2026-09-27",
            "temporal_authority": "PROVIDER_CAREER_CANDIDATE",
            "evidence_quality": "PROVIDER",
            "notes": (
                "Point14 V17 archive-first provider career evidence."
            ),
        }

        comparison = compare_candidate_to_verified(
            candidate,
            verified,
        )

        if comparison.get("automatic_promotion") is not False:
            raise RuntimeError(
                f"Automatic promotion unexpectedly enabled for team {team_id}"
            )

        candidates.append(
            {
                "provider_row": row,
                "candidate": candidate,
                "comparison": comparison,
            }
        )

    results.append(
        {
            "team_id": team_id,
            "team_name": team_name,
            "career_row_count": len(team_rows),
            "candidates": candidates,
        }
    )

after = broker.stats()
calls_after = real_calls(after)
provider_calls = calls_after - calls_before

if provider_calls > 2:
    raise RuntimeError(
        f"Provider call cap violated: {provider_calls}"
    )

result = {
    "version": "PBK_POINT14_COACH_PROVIDER_V17",
    "targets": results,
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

print("=" * 100)
print("PBK POINT14 V17 — ARCHIVE-FIRST COACH PROVIDER PROOF")
print("=" * 100)

for target in results:
    print()
    print(
        f"TEAM {target['team_id']} — {target['team_name']}"
    )
    for item in target["candidates"]:
        print(
            json.dumps(
                item,
                ensure_ascii=False,
            )
        )

print()
print("=" * 100)
print("V17 SUMMARY")
print("=" * 100)
print(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )
)

print()
print("POINT14 COACH PROVIDER V17 PASSED")
