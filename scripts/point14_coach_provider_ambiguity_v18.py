from __future__ import annotations

import json
import os
from pathlib import Path

# V18 proof MUST be archive-only. Any archive miss must fail rather than burn API quota.
os.environ["API_FOOTBALL_MAX_REAL_CALLS"] = "0"

from scripts.api_football_broker import get_broker
from scripts.coach_provider_ambiguity import (
    assess_provider_career_ambiguity,
)


TARGETS = [
    ("47", "Tottenham", "PROVIDER_CAREER_AMBIGUOUS", 4),
    ("496", "Juventus", "PROVIDER_CAREER_AMBIGUOUS", 2),
]

OPS = Path("ops")
OUT = OPS / "point14_coach_provider_ambiguity_v18.json"


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
            continue

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

before = broker.stats()
calls_before = real_calls(before)

results = []

for (
    team_id,
    team_name,
    expected_status,
    expected_distinct_active,
) in TARGETS:
    payload = broker.get(
        "/coachs",
        {"team": team_id},
        archive_first=True,
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Archived payload for team {team_id} is not a dict"
        )

    if payload.get("errors"):
        raise RuntimeError(
            f"Archived provider payload has errors for team {team_id}: "
            f"{payload.get('errors')}"
        )

    rows = extract_team_rows(
        payload,
        team_id,
    )

    if not rows:
        raise RuntimeError(
            f"No archived career rows for team {team_id}"
        )

    assessment = assess_provider_career_ambiguity(
        rows,
        team_id=team_id,
        as_of_date="2026-09-27",
    )

    if assessment.get("status") != expected_status:
        raise RuntimeError(
            f"Unexpected ambiguity status for team {team_id}: "
            f"{assessment.get('status')} != {expected_status}"
        )

    if (
        int(assessment.get("distinct_active_coach_count") or 0)
        != expected_distinct_active
    ):
        raise RuntimeError(
            f"Unexpected distinct active coach count for team {team_id}: "
            f"{assessment.get('distinct_active_coach_count')} "
            f"!= {expected_distinct_active}"
        )

    if assessment.get("selected_candidate") is not None:
        raise RuntimeError(
            f"Ambiguous provider evidence selected a coach for team {team_id}"
        )

    if assessment.get("automatic_promotion") is not False:
        raise RuntimeError(
            f"Automatic promotion unexpectedly enabled for team {team_id}"
        )

    if assessment.get("operational_betting_authority") is not False:
        raise RuntimeError(
            f"Operational authority unexpectedly enabled for team {team_id}"
        )

    results.append(
        {
            "team_id": team_id,
            "team_name": team_name,
            "career_row_count": len(rows),
            "assessment": assessment,
        }
    )

after = broker.stats()
calls_after = real_calls(after)
provider_calls = calls_after - calls_before

if provider_calls != 0:
    raise RuntimeError(
        f"V18 archive-only proof made real provider calls: {provider_calls}"
    )

archive_hits = (
    int(after.get("archive_read_hits") or 0)
    - int(before.get("archive_read_hits") or 0)
)

archive_misses = (
    int(after.get("archive_read_misses") or 0)
    - int(before.get("archive_read_misses") or 0)
)

if archive_hits != 2:
    raise RuntimeError(
        f"Expected exactly 2 archive hits, got {archive_hits}"
    )

if archive_misses != 0:
    raise RuntimeError(
        f"Expected zero archive misses, got {archive_misses}"
    )

result = {
    "version": "PBK_POINT14_COACH_PROVIDER_AMBIGUITY_V18",
    "targets": results,
    "provider_calls_this_proof": provider_calls,
    "archive_only": True,
    "archive_first": True,
    "archive_enabled": after.get("archive_enabled"),
    "archive_backend": after.get("archive_backend"),
    "archive_read_hits_delta": archive_hits,
    "archive_read_misses_delta": archive_misses,
    "coach_tenure_history_mutation": False,
    "automatic_promotion": False,
    "research_only": True,
    "operational_betting_authority": False,
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
print("PBK POINT14 V18 — ARCHIVE-ONLY COACH PROVIDER AMBIGUITY PROOF")
print("=" * 100)

for target in results:
    assessment = target["assessment"]
    print(
        f"{target['team_id']} {target['team_name']}: "
        f"{assessment['status']} | "
        f"active={assessment['distinct_active_coach_count']} | "
        f"selected={assessment['selected_candidate']}"
    )

print()
print(json.dumps(result, ensure_ascii=False, indent=2))
print()
print("POINT14 COACH PROVIDER AMBIGUITY V18 PASSED")
