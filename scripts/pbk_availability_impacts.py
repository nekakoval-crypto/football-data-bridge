#!/usr/bin/env python3
"""PBK availability / return / rotation impact research foundation.

Provider-free and fail-closed. Observed evidence is kept separate from impact
inference. No canonical signal, probability, EV, stake, settlement or forward
journal state is mutated here.
"""
from __future__ import annotations

import math
from datetime import datetime
from statistics import mean
from typing import Any

PRESENT_STATES = {"PRESENT", "STARTER", "BENCH"}
ABSENT_STATES = {"ABSENT"}
ALLOWED_STATES = PRESENT_STATES | ABSENT_STATES | {"UNKNOWN"}


def _num(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def _pid(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("player_id") or "").strip()


def _grade_map(rows: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, float]:
    if isinstance(rows, dict):
        source = rows.items()
    else:
        source = ((row.get("player_id"), row.get("grade", row.get("overall_grade"))) for row in (rows or []))
    out: dict[str, float] = {}
    for player_id, value in source:
        pid = str(player_id or "").strip()
        grade = _num(value)
        if pid and grade is not None:
            out[pid] = grade
    return out


def observed_player_timeline(
    events: list[dict[str, Any]],
    player_id: str,
    before_utc: str,
    *,
    team_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return explicit availability evidence known no later than `before_utc`."""
    cutoff = _iso(before_utc)
    if cutoff is None:
        raise ValueError("aware before_utc is required")
    output: list[tuple[datetime, dict[str, Any]]] = []
    for row in events or []:
        if str(row.get("player_id") or "").strip() != str(player_id).strip():
            continue
        if team_id is not None and str(row.get("team_id") or "").strip() != str(team_id).strip():
            continue
        observed = _iso(row.get("observed_at_utc"))
        if observed is None or observed > cutoff:
            continue
        state = str(row.get("state") or "UNKNOWN").strip().upper()
        if state not in ALLOWED_STATES:
            raise ValueError(f"unsupported availability state: {state}")
        normalized = dict(row)
        normalized["state"] = state
        output.append((observed, normalized))
    output.sort(key=lambda item: item[0])
    return [row for _, row in output]


def absence_impact_components(
    events: list[dict[str, Any]],
    player_id: str,
    team_id: str,
    before_utc: str,
    *,
    importance_row: dict[str, Any] | None = None,
    player_grade: float | None = None,
    replacement_grade: float | None = None,
) -> dict[str, Any]:
    """Describe a confirmed absence without inventing a combined impact score."""
    timeline = observed_player_timeline(events, player_id, before_utc, team_id=team_id)
    latest = timeline[-1] if timeline else None
    confirmed = bool(latest and latest.get("state") == "ABSENT")

    importance = importance_row or {}
    importance_eligible = str(importance.get("eligible") or "").strip().lower() == "true"
    importance_score = _num(importance.get("importance_score")) if importance_eligible else None
    p_grade = _num(player_grade)
    r_grade = _num(replacement_grade)
    replacement_gap = round(p_grade - r_grade, 3) if p_grade is not None and r_grade is not None else None

    blockers: list[str] = []
    if not confirmed:
        blockers.append("NO_EXPLICIT_CONFIRMED_ABSENCE")
    if importance_score is None:
        blockers.append("NO_ELIGIBLE_IMPORTANCE_EVIDENCE")
    if p_grade is None:
        blockers.append("NO_PLAYER_GRADE")
    if r_grade is None:
        blockers.append("NO_REPLACEMENT_GRADE")

    return {
        "version": "PBK_ABSENCE_IMPACT_FOUNDATION_V1",
        "player_id": str(player_id),
        "team_id": str(team_id),
        "before_utc": before_utc,
        "confirmed_absence": confirmed,
        "latest_explicit_state": latest.get("state") if latest else None,
        "latest_source": latest.get("source") if latest else None,
        "latest_observed_at_utc": latest.get("observed_at_utc") if latest else None,
        "importance_score": importance_score,
        "player_grade": p_grade,
        "replacement_grade": r_grade,
        "replacement_quality_gap": replacement_gap,
        "candidate_total_impact": None,
        "candidate_total_impact_status": "FORBIDDEN_UNTIL_WEIGHTING_VALIDATED",
        "status": "COMPONENTS_AVAILABLE" if confirmed and not blockers else "DATA_BLOCKED",
        "blockers": blockers,
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def _current_presence_run(timeline: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split timeline into history and the trailing uninterrupted presence run."""
    if not timeline or timeline[-1].get("state") not in PRESENT_STATES:
        return timeline, []
    start = len(timeline) - 1
    while start > 0 and timeline[start - 1].get("state") in PRESENT_STATES:
        start -= 1
    return timeline[:start], timeline[start:]


def return_event(
    events: list[dict[str, Any]],
    player_id: str,
    team_id: str,
    before_utc: str,
    *,
    min_prior_absent_events: int = 1,
) -> dict[str, Any]:
    """Detect an evidence-backed return from the immediately preceding state run.

    Historical absence somewhere in the past is insufficient. The current
    uninterrupted presence run must be immediately preceded by an explicit
    ABSENT run. UNKNOWN breaks the chain and therefore fails closed.
    """
    timeline = observed_player_timeline(events, player_id, before_utc, team_id=team_id)
    latest = timeline[-1] if timeline else None
    latest_state = latest.get("state") if latest else None
    history, presence_run = _current_presence_run(timeline)
    latest_is_present = bool(presence_run)

    prior_absent_run: list[dict[str, Any]] = []
    if latest_is_present:
        index = len(history) - 1
        while index >= 0 and history[index].get("state") == "ABSENT":
            prior_absent_run.append(history[index])
            index -= 1
        prior_absent_run.reverse()

    required = max(1, int(min_prior_absent_events))
    returned = bool(latest_is_present and len(prior_absent_run) >= required)
    last_absent = prior_absent_run[-1] if prior_absent_run else None
    first_present = presence_run[0] if presence_run else None

    blockers: list[str] = []
    if not latest_is_present:
        blockers.append("NO_EXPLICIT_CURRENT_PRESENCE")
    if len(prior_absent_run) < required:
        blockers.append("NO_EXPLICIT_PRIOR_ABSENCE_RUN")

    return {
        "version": "PBK_RETURN_EVENT_FOUNDATION_V1",
        "player_id": str(player_id),
        "team_id": str(team_id),
        "before_utc": before_utc,
        "return_event": returned,
        "current_state": latest_state,
        "current_observed_at_utc": latest.get("observed_at_utc") if latest else None,
        "return_observed_at_utc": first_present.get("observed_at_utc") if returned and first_present else None,
        "prior_absent_events": len(prior_absent_run),
        "last_absent_observed_at_utc": last_absent.get("observed_at_utc") if last_absent else None,
        "return_impact_score": None,
        "return_impact_status": "NOT_AUTHORIZED_WITHOUT_VALIDATED_OUTCOME_MODEL",
        "blockers": blockers,
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def rotation_quality_components(
    current_xi: list[dict[str, Any]],
    previous_xi: list[dict[str, Any]],
    player_grades: list[dict[str, Any]] | dict[str, Any] | None,
    *,
    minimum_quality_coverage: int = 8,
) -> dict[str, Any]:
    """Measure XI membership turnover and quality delta without causal claims."""
    current_ids = {_pid(row) for row in current_xi or [] if _pid(row)}
    previous_ids = {_pid(row) for row in previous_xi or [] if _pid(row)}
    grades = _grade_map(player_grades)

    changed_in = sorted(current_ids - previous_ids)
    changed_out = sorted(previous_ids - current_ids)
    retained = sorted(current_ids & previous_ids)
    current_values = [grades[pid] for pid in current_ids if pid in grades]
    previous_values = [grades[pid] for pid in previous_ids if pid in grades]

    current_quality = round(mean(current_values), 3) if current_values else None
    previous_quality = round(mean(previous_values), 3) if previous_values else None
    current_covered = len(current_values)
    previous_covered = len(previous_values)
    complete_xis = len(current_ids) == 11 and len(previous_ids) == 11
    quality_ready = (
        complete_xis
        and current_quality is not None
        and previous_quality is not None
        and current_covered >= minimum_quality_coverage
        and previous_covered >= minimum_quality_coverage
    )
    delta = round(current_quality - previous_quality, 3) if quality_ready else None

    blockers: list[str] = []
    if len(current_ids) != 11:
        blockers.append("CURRENT_XI_NOT_COMPLETE")
    if len(previous_ids) != 11:
        blockers.append("PREVIOUS_XI_NOT_COMPLETE")
    if current_covered < minimum_quality_coverage:
        blockers.append("CURRENT_XI_GRADE_COVERAGE_LOW")
    if previous_covered < minimum_quality_coverage:
        blockers.append("PREVIOUS_XI_GRADE_COVERAGE_LOW")

    return {
        "version": "PBK_ROTATION_QUALITY_FOUNDATION_V1",
        "current_xi_count": len(current_ids),
        "previous_xi_count": len(previous_ids),
        "retained_starters": len(retained),
        "changed_starters": len(changed_in) if complete_xis else None,
        "changed_in_player_ids": changed_in,
        "changed_out_player_ids": changed_out,
        "current_xi_quality": current_quality,
        "previous_xi_quality": previous_quality,
        "current_grade_coverage": current_covered,
        "previous_grade_coverage": previous_covered,
        "minimum_quality_coverage": minimum_quality_coverage,
        "quality_delta": delta,
        "quality_delta_status": "RESEARCH_COMPONENT" if delta is not None else "DATA_BLOCKED",
        "rotation_impact_score": None,
        "rotation_impact_status": "NOT_AUTHORIZED_WITHOUT_VALIDATION",
        "blockers": blockers,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }
