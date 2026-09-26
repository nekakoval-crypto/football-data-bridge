#!/usr/bin/env python3
"""PBK Team + Player Grade foundation.

This module deliberately separates three different truths:
1) a player match grade can be COMPUTED from captured player evidence;
2) rolling player form can be DESCRIBED only from evidence known before kickoff;
3) team component grades remain INDEPENDENT research components until each
   component is validated. There is no Team Overall weighted average here.

No provider calls are made and no canonical signal/probability/value/stake state
is mutated.
"""
from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any
from player_snapshot_store import read_snapshot_rows

ROOT = Path(__file__).resolve().parents[1]
OPS = Path(os.getenv("OPS_DIR", "ops"))
OUT = OPS / "team_player_grade_readiness.json"

TEAM_COMPONENTS = (
    "ATTACK",
    "DEFENCE",
    "FORM",
    "HOME",
    "AWAY",
    "SCHEDULE_FATIGUE",
    "SQUAD",
    "XI_QUALITY",
    "AVAILABILITY",
    "MOTIVATION",
    "MARKET",
)

VALIDATION_STATUSES = {
    "DATA_MISSING",
    "RAW_EVIDENCE_ONLY",
    "PROXY_LIMITED",
    "VALIDATION_PENDING",
    "VALIDATED",
}


def fnum(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_iso(value: Any):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _mean(values: list[float]) -> float | None:
    return round(mean(values), 3) if values else None


def player_form_profile(
    grade_rows: list[dict[str, Any]],
    player_id: str,
    before_utc: str,
    *,
    season: str | int | None = None,
    min_minutes: int = 30,
) -> dict[str, Any]:
    """Return Last/Form3/Form5/Form10/Season using only prior captured evidence.

    `season` must be explicitly supplied for a season baseline. We do not infer a
    season boundary from the date because that can be wrong across competitions.
    Rows observed after the target kickoff are rejected even when their match date
    is older, preserving no-lookahead semantics.
    """
    cutoff = parse_iso(before_utc)
    if cutoff is None:
        raise ValueError("aware before_utc is required")

    eligible: list[tuple[datetime, float, dict[str, Any]]] = []
    low_minutes_excluded = 0
    post_cutoff_excluded = 0
    for row in grade_rows or []:
        if str(row.get("player_id") or "").strip() != str(player_id).strip():
            continue
        kickoff = parse_iso(row.get("kickoff_utc"))
        observed = parse_iso(row.get("observed_at_utc"))
        if kickoff is None or kickoff >= cutoff:
            post_cutoff_excluded += 1
            continue
        if observed is not None and observed > cutoff:
            post_cutoff_excluded += 1
            continue
        grade = fnum(row.get("overall_grade"))
        if grade is None:
            continue
        minutes = fnum(row.get("minutes")) or 0.0
        if minutes < min_minutes:
            low_minutes_excluded += 1
            continue
        eligible.append((kickoff, grade, row))

    eligible.sort(key=lambda item: item[0], reverse=True)
    grades = [item[1] for item in eligible]

    def window(size: int) -> tuple[float | None, int]:
        sample = grades[:size]
        return _mean(sample), len(sample)

    form3, sample3 = window(3)
    form5, sample5 = window(5)
    form10, sample10 = window(10)
    last = grades[0] if grades else None

    season_rows: list[float] = []
    season_status = "SEASON_NOT_REQUESTED"
    if season is not None:
        wanted = str(season)
        season_rows = [
            item[1] for item in eligible
            if str(item[2].get("season") or "").strip() == wanted
        ]
        season_status = "OK" if season_rows else "NO_SEASON_ROWS"
    season_grade = _mean(season_rows)

    trend_3_vs_10 = (
        round(form3 - form10, 3)
        if form3 is not None and form10 is not None and sample10 >= 3
        else None
    )
    deviation_last_vs_season = (
        round(last - season_grade, 3)
        if last is not None and season_grade is not None
        else None
    )

    confidence = "UNKNOWN"
    if sample10 >= 8:
        confidence = "HIGH"
    elif sample5 >= 3:
        confidence = "MEDIUM"
    elif grades:
        confidence = "LOW"

    return {
        "version": "PBK_PLAYER_FORM_PROFILE_V1",
        "player_id": str(player_id),
        "before_utc": before_utc,
        "min_minutes": min_minutes,
        "last": last,
        "form_3": form3,
        "form_5": form5,
        "form_10": form10,
        "season": season_grade,
        "season_label": None if season is None else str(season),
        "season_status": season_status,
        "sample_3": sample3,
        "sample_5": sample5,
        "sample_10": sample10,
        "sample_season": len(season_rows),
        "trend_3_vs_10": trend_3_vs_10,
        "deviation_last_vs_season": deviation_last_vs_season,
        "confidence": confidence,
        "low_minutes_excluded": low_minutes_excluded,
        "post_cutoff_excluded": post_cutoff_excluded,
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def team_component_vector(evidence: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Normalize independent team components without inventing Team Overall.

    A component may carry a research `candidate_grade` only when a component
    producer supplied one. It becomes `official_grade` only when that component
    explicitly declares VALIDATED. The function never averages components.
    """
    evidence = evidence or {}
    components: dict[str, Any] = {}
    for name in TEAM_COMPONENTS:
        source = dict(evidence.get(name) or {})
        status = str(source.get("validation_status") or "DATA_MISSING").upper()
        if status not in VALIDATION_STATUSES:
            raise ValueError(f"{name}: unsupported validation_status {status}")
        candidate = fnum(source.get("candidate_grade"))
        if candidate is not None and not 0.0 <= candidate <= 10.0:
            raise ValueError(f"{name}: candidate_grade must be within 0..10")
        official = candidate if status == "VALIDATED" else None
        components[name] = {
            "validation_status": status,
            "candidate_grade": candidate,
            "official_grade": official,
            "source": source.get("source"),
            "sample_size": source.get("sample_size"),
            "confidence": source.get("confidence") or "UNKNOWN",
            "limitations": list(source.get("limitations") or []),
        }

    return {
        "version": "PBK_TEAM_COMPONENT_VECTOR_V1",
        "components": components,
        "team_overall_grade": None,
        "team_overall_status": "FORBIDDEN_UNTIL_COMPONENT_VALIDATION",
        "component_weighting": None,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def runtime_readiness(ops_dir: Path = OPS) -> dict[str, Any]:
    """Materialize honest runtime readiness from already-captured operational data."""
    stage77 = read_json(ops_dir / "stage77_last_run.json")
    stage78 = read_json(ops_dir / "stage78_last_run.json")
    grade_rows = read_snapshot_rows(ops_dir / "player_grade_snapshots.csv")
    stats_rows = read_snapshot_rows(ops_dir / "player_stats_snapshots.csv")
    xi_rows = read_csv(ops_dir / "xi_quality_history.csv")
    importance_rows = read_csv(ops_dir / "player_importance_research.csv")
    context_rows = read_csv(ops_dir / "context_latest.csv")

    player_data_ready = bool(grade_rows)
    xi_data_ready = any(fnum(row.get("xi_quality")) is not None for row in xi_rows)
    importance_ready = any(str(row.get("eligible") or "").lower() == "true" for row in importance_rows)
    context_available = bool(context_rows)

    blockers = []
    if not player_data_ready:
        blockers.append("NO_PLAYER_GRADE_ROWS")
    if not xi_data_ready:
        blockers.append("NO_POPULATED_XI_QUALITY_ROWS")
    if not importance_ready:
        blockers.append("NO_ELIGIBLE_PLAYER_IMPORTANCE_ROWS")

    return {
        "version": "PBK_TEAM_PLAYER_GRADE_READINESS_V1",
        "status": "DATA_READY_FOR_VALIDATION" if not blockers else "PARTIAL_DATA_BLOCKED",
        "player": {
            "stats_rows": len(stats_rows),
            "grade_rows": len(grade_rows),
            "form_profile_code_ready": True,
            "form_windows": [3, 5, 10, "SEASON"],
            "player_data_ready": player_data_ready,
            "stage77_status": stage77.get("status"),
            "stage77_backlog_pending": stage77.get("backlog_pending"),
        },
        "xi_and_importance": {
            "xi_quality_rows": len(xi_rows),
            "populated_xi_quality": xi_data_ready,
            "importance_rows": len(importance_rows),
            "importance_eligible": importance_ready,
            "stage78_status": stage78.get("status"),
        },
        "team": {
            "component_vector_code_ready": True,
            "component_ids": list(TEAM_COMPONENTS),
            "context_rows": len(context_rows),
            "context_evidence_available": context_available,
            "team_overall_grade": None,
            "team_overall_status": "NOT_AUTHORIZED",
        },
        "blockers": blockers,
        "policy": {
            "provider_calls_added": 0,
            "no_arbitrary_team_average": True,
            "no_lookahead_player_form": True,
            "signals_created": 0,
            "probability_mutation": False,
            "eligibility_mutation": False,
            "stake_changes": False,
            "forward_journal_mutation": False,
            "ui_changes": False,
        },
    }


def run(ops_dir: Path = OPS, output: Path | None = None) -> dict[str, Any]:
    payload = runtime_readiness(Path(ops_dir))
    target = output or (Path(ops_dir) / OUT.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, target)
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
