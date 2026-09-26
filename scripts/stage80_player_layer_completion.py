#!/usr/bin/env python3
"""Stage80 player-layer completion research/readiness audit.

Provider-free and fail-closed. This stage materializes only research evidence
from already persisted PBK files. It does not create signals, probabilities,
eligibility, stakes, EV, settlement or Forward Journal mutations.

Purpose:
- reconstruct retrospective availability evidence without pretending it was
  known pre-kickoff;
- materialize structural XI/rotation features from historical official lineups;
- keep Player Quality, Current Form, Availability, Rotation and International
  Load as distinct components;
- publish a final machine-readable readiness audit for checklist item 10.

Historical lineup/injury inputs are RETROSPECTIVE_ONLY unless a separate source
proves a pre-match observation timestamp.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from player_snapshot_store import read_snapshot_rows

OPS = Path(os.getenv("OPS_DIR", "ops"))

GRADES = OPS / "player_grade_snapshots.csv"
FORM = OPS / "player_form_walk_forward.csv"
IMPORTANCE = OPS / "player_importance_research.csv"
HIST_LINEUPS = OPS / "historical_lineup_snapshots.csv"
HIST_INJURIES = OPS / "historical_injury_snapshots.csv"
INT_RETURN = OPS / "international_duty_player_return_load.csv"
STAGE77_META = OPS / "stage77_historical_player_backfill_last_run.json"
STAGE78_META = OPS / "stage78_player_form_walk_forward_last_run.json"
AVAILABILITY_OUT = OPS / "player_layer_availability_research.csv"
ROTATION_OUT = OPS / "player_layer_rotation_research.csv"
READINESS_OUT = OPS / "player_layer_completion_readiness.json"

VERSION = "PBK_STAGE80_PLAYER_LAYER_COMPLETION_V1"

AVAILABILITY_FIELDS = [
    "fixture_id", "kickoff_utc", "team_id", "team_name", "player_id",
    "player_name", "injury_type", "injury_reason", "retrieved_at_utc",
    "evidence_state", "temporal_authority", "prematch_known",
    "impact_score", "impact_authority", "research_only",
]

ROTATION_FIELDS = [
    "team_id", "team_name", "fixture_id", "kickoff_utc",
    "previous_fixture_id", "previous_kickoff_utc",
    "current_xi_count", "previous_xi_count", "retained_starters",
    "changed_in_count", "changed_out_count",
    "changed_in_player_ids_json", "changed_out_player_ids_json",
    "xi_stability_pct", "quality_delta", "quality_delta_status",
    "temporal_authority", "prematch_known", "research_only",
]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def write_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def parse_xi(value):
    """Return an ordered list of unique player IDs or [] for an incomplete XI."""
    try:
        raw = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list) or len(raw) != 11:
        return []
    ids = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            return []
        player = item.get("player") if isinstance(item.get("player"), dict) else item
        pid = str(player.get("id") or player.get("player_id") or "").strip()
        if not pid or pid in seen:
            return []
        seen.add(pid)
        ids.append(pid)
    return ids


def _field(row, *names):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value)
    return ""


def build_availability_rows(injury_rows):
    """Keep retrospective injury evidence explicit and non-causal."""
    out = []
    seen = set()
    for row in injury_rows:
        fixture_id = _field(row, "fixture_id", "api_fixture_id")
        team_id = _field(row, "team_id")
        player_id = _field(row, "player_id")
        if not fixture_id or not player_id:
            continue
        key = (
            fixture_id,
            team_id,
            player_id,
            _field(row, "type", "injury_type"),
            _field(row, "reason", "injury_reason"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "fixture_id": fixture_id,
            "kickoff_utc": _field(row, "kickoff_utc"),
            "team_id": team_id,
            "team_name": _field(row, "team_name"),
            "player_id": player_id,
            "player_name": _field(row, "player_name"),
            "injury_type": _field(row, "type", "injury_type"),
            "injury_reason": _field(row, "reason", "injury_reason"),
            "retrieved_at_utc": _field(row, "retrieved_at_utc"),
            "evidence_state": "RETROSPECTIVE_INJURY_EVIDENCE",
            "temporal_authority": "RETROSPECTIVE_ONLY",
            "prematch_known": "NO",
            "impact_score": "",
            "impact_authority": "NOT_AUTHORIZED_WITHOUT_PREMATCH_EVIDENCE_AND_VALIDATION",
            "research_only": "YES",
        })
    return sorted(out, key=lambda r: (
        r["kickoff_utc"], r["fixture_id"], r["team_id"], r["player_id"]
    ))


def build_rotation_rows(lineup_rows):
    """Build structural XI turnover only; do not infer causal quality impact."""
    by_team = defaultdict(list)
    for row in lineup_rows:
        team_id = _field(row, "team_id")
        fixture_id = _field(row, "fixture_id", "api_fixture_id")
        kickoff = _field(row, "kickoff_utc")
        xi = parse_xi(row.get("starting_xi_json"))
        if not team_id or not fixture_id or not kickoff or len(xi) != 11:
            continue
        by_team[team_id].append({
            "team_id": team_id,
            "team_name": _field(row, "team_name"),
            "fixture_id": fixture_id,
            "kickoff_utc": kickoff,
            "xi": xi,
        })

    out = []
    for team_id, observations in by_team.items():
        observations.sort(key=lambda r: (r["kickoff_utc"], r["fixture_id"]))
        previous = None
        for current in observations:
            if previous is None:
                previous = current
                continue
            current_set = set(current["xi"])
            previous_set = set(previous["xi"])
            retained = sorted(current_set & previous_set)
            changed_in = sorted(current_set - previous_set)
            changed_out = sorted(previous_set - current_set)
            out.append({
                "team_id": team_id,
                "team_name": current["team_name"] or previous["team_name"],
                "fixture_id": current["fixture_id"],
                "kickoff_utc": current["kickoff_utc"],
                "previous_fixture_id": previous["fixture_id"],
                "previous_kickoff_utc": previous["kickoff_utc"],
                "current_xi_count": 11,
                "previous_xi_count": 11,
                "retained_starters": len(retained),
                "changed_in_count": len(changed_in),
                "changed_out_count": len(changed_out),
                "changed_in_player_ids_json": json.dumps(changed_in, ensure_ascii=False),
                "changed_out_player_ids_json": json.dumps(changed_out, ensure_ascii=False),
                "xi_stability_pct": round(100.0 * len(retained) / 11.0, 3),
                "quality_delta": "",
                "quality_delta_status": "BLOCKED_UNTIL_STRICTLY_PRIOR_PLAYER_QUALITY_JOIN",
                "temporal_authority": "RETROSPECTIVE_ONLY",
                "prematch_known": "NO",
                "research_only": "YES",
            })
            previous = current
    return sorted(out, key=lambda r: (r["kickoff_utc"], r["team_id"], r["fixture_id"]))


def _component(status, evidence, blockers=None, authority="RESEARCH"):
    return {
        "status": status,
        "authority": authority,
        "evidence": evidence,
        "blockers": blockers or [],
    }


def build_readiness(
    grade_rows,
    form_rows,
    importance_rows,
    availability_rows,
    rotation_rows,
    international_rows,
    stage77_meta,
    stage78_meta,
):
    grade_count = len(grade_rows)
    form_count = len(form_rows)
    importance_count = len(importance_rows)
    availability_count = len(availability_rows)
    rotation_count = len(rotation_rows)
    international_count = len(international_rows)
    leakage = int(stage78_meta.get("leakage_violations") or 0)

    components = {
        "PLAYER_QUALITY": _component(
            "VALIDATION_PENDING" if grade_count else "DATA_MISSING",
            {
                "player_grade_rows": grade_count,
                "historical_player_backfill_status": stage77_meta.get("status"),
                "historical_player_remaining": stage77_meta.get("remaining_unattempted_or_retryable"),
            },
            [] if grade_count else ["NO_PLAYER_GRADE_ROWS"],
        ),
        "CURRENT_FORM": _component(
            "VALIDATION_PENDING" if form_count and leakage == 0 else "RESEARCH_ONLY",
            {
                "walk_forward_rows": form_count,
                "leakage_violations": leakage,
                "no_lookahead": stage78_meta.get("no_lookahead"),
            },
            [] if form_count and leakage == 0 else ["FORM_WALK_FORWARD_NOT_READY"],
        ),
        "PLAYER_IMPORTANCE": _component(
            "VALIDATION_PENDING" if importance_count else "RESEARCH_ONLY",
            {"importance_rows": importance_count},
            [] if importance_count else ["IMPORTANCE_EVIDENCE_INCOMPLETE"],
        ),
        "AVAILABILITY": _component(
            "RESEARCH_ONLY",
            {
                "retrospective_injury_evidence_rows": availability_count,
                "temporal_authority": "RETROSPECTIVE_ONLY",
                "prematch_known": False,
            },
            [
                "HISTORICAL_INJURY_RETRIEVAL_TIME_IS_NOT_PREMATCH_OBSERVATION_TIME",
                "IMPACT_WEIGHTING_NOT_VALIDATED",
            ],
        ),
        "XI_ROTATION": _component(
            "RESEARCH_ONLY",
            {
                "structural_rotation_rows": rotation_count,
                "quality_delta_authorized": False,
                "temporal_authority": "RETROSPECTIVE_ONLY",
            },
            [
                "STRICTLY_PRIOR_PLAYER_QUALITY_JOIN_REQUIRED_FOR_QUALITY_DELTA",
                "ROTATION_OUTCOME_MODEL_NOT_VALIDATED",
            ],
        ),
        "INTERNATIONAL_RETURN_LOAD": _component(
            "VALIDATION_PENDING" if international_count else "RESEARCH_ONLY",
            {"return_load_rows": international_count},
            [] if international_count else ["NO_RETURN_LOAD_ROWS"],
        ),
        "SEPARATION_AND_DOUBLE_COUNTING_GUARD": _component(
            "OPERATIONAL_AUTHORIZED",
            {
                "dimensions": [
                    "PLAYER_QUALITY",
                    "CURRENT_FORM",
                    "PLAYER_IMPORTANCE",
                    "AVAILABILITY",
                    "XI_ROTATION",
                    "INTERNATIONAL_RETURN_LOAD",
                ],
                "raw_additive_mega_score_forbidden": True,
                "specialist_model_required": True,
            },
            authority="GOVERNANCE",
        ),
    }

    predictive = [
        value["status"]
        for key, value in components.items()
        if key != "SEPARATION_AND_DOUBLE_COUNTING_GUARD"
    ]
    if all(status == "DATA_MISSING" for status in predictive):
        overall = "DATA_MISSING"
    elif any(status == "VALIDATION_PENDING" for status in predictive):
        overall = "VALIDATION_PENDING"
    else:
        overall = "RESEARCH_ONLY"

    return {
        "version": VERSION,
        "run_at_utc": now_iso(),
        "status": overall,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "components": components,
        "separation_contract": {
            "PLAYER_QUALITY": "stable/prior capability evidence; never short-term form",
            "CURRENT_FORM": "recent deviation/trend; never a substitute for stable quality",
            "PLAYER_IMPORTANCE": "role/minutes/replacement context; not the same as quality",
            "AVAILABILITY": "presence/absence/return evidence only",
            "XI_ROTATION": "membership/structural change; do not relabel as absence",
            "INTERNATIONAL_RETURN_LOAD": "travel/minutes/load context; distinct from club form",
            "double_counting_rule": (
                "The same raw observation may feed multiple descriptive views, "
                "but a decision model must de-duplicate shared evidence and may "
                "not sum raw component scores without separate validation."
            ),
        },
        "next_gates": [
            "continue historical player backfill",
            "continue historical lineup/injury backfill",
            "build strictly-prior player-quality join for XI quality delta",
            "validate absence/return impact with genuine prematch evidence",
            "validate rotation features against outcomes/markets without lookahead",
            "only then consider OPERATIONAL_AUTHORIZED predictive authority",
        ],
    }


def main():
    grade_rows = read_snapshot_rows(GRADES)
    form_rows = read_csv(FORM)
    importance_rows = read_csv(IMPORTANCE)
    injury_rows = read_csv(HIST_INJURIES)
    lineup_rows = read_csv(HIST_LINEUPS)
    international_rows = read_csv(INT_RETURN)
    stage77_meta = read_json(STAGE77_META)
    stage78_meta = read_json(STAGE78_META)

    availability_rows = build_availability_rows(injury_rows)
    rotation_rows = build_rotation_rows(lineup_rows)

    write_csv(AVAILABILITY_OUT, AVAILABILITY_FIELDS, availability_rows)
    write_csv(ROTATION_OUT, ROTATION_FIELDS, rotation_rows)

    readiness = build_readiness(
        grade_rows,
        form_rows,
        importance_rows,
        availability_rows,
        rotation_rows,
        international_rows,
        stage77_meta,
        stage78_meta,
    )
    READINESS_OUT.write_text(
        json.dumps(readiness, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(readiness, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
