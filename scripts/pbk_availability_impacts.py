#!/usr/bin/env python3
"""PBK availability / return / rotation impact research foundation.

This module is deliberately provider-free and fail-closed.

It separates *observed evidence* from *impact inference*:
- ABSENCE requires an explicit observed availability state. A player missing from
  the starting XI is never silently called injured/suspended/absent.
- RETURN requires an observed transition from explicit ABSENT evidence to an
  explicit PRESENT/STARTER/BENCH state. Missing observations do not create a
  return event.
- ROTATION QUALITY compares official/current XI membership and pre-kickoff
  player-grade evidence. It exposes coverage, changed players and quality delta;
  it does not turn that delta into a betting signal or probability adjustment.

No canonical R1/R2/R3 eligibility, probability, EV, stake, settlement or forward
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
    """Return explicit availability evidence known no later than `before_utc`.

    Events without an aware observation timestamp are ignored. This prevents an
    undated injury/availability claim from leaking into a pre-match state.
    """
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
    """Describe an explicit confirmed absence without inventing a total impact.

    The latest explicit availability event must be ABSENT. Importance, player
    grade and replacement quality remain separate components until a weighting
    method is validated out of sample.
    """
    timeline = observed_player_timeline(events, player_id, before_utc, team_id=team_id)
    latest = timeline[-1] if timeline else None
    confirmed = bool(latest and latest.get("state") == "ABSENT")

    importance = importance_row or {}
    importance_eligible = str(importance.get("eligible") or "").strip().lower() == "true"
    importance_score = _num(importance.get("importance_score")) if importance_eligible else None
    p_grade = _num(player_grade)
    r_grade = _num(replacement_grade)
    replacement_gap = round(p_grade - r_grade, 3) if p_grade is not None and r_grade is not None else None

    blockers = []
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
        "status": "COMPONENTS_AVAILABLE" if confirmed and not blockers[1:] else "DATA_BLOCKED",
        "blockers": blockers,
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def return_event(
    events: list[dict[str, Any]],
    player_id: str,
    team_id: str,
    before_utc: str,
    *,
    min_prior_absent_events: int = 1,
) -> dict[str, Any]:
    """Detect an evidence-backed return, not a guessed medical recovery.

    A return exists only when the latest explicit state is PRESENT/STARTER/BENCH
    and at least `min_prior_absent_events` explicit ABSENT observations precede
    that latest presence state.
    """
    timeline = observed_player_timeline(events, player_id, before_utc, team_id=team_id)
    latest = timeline[-1] if timeline else None
    latest_state = latest.get("state") if latest else None
    latest_is_present = latest_state in PRESENT_STATES
    prior = timeline[:-1] if latest else []
    prior_absent = [row for row in prior if row.get("state") == "ABSENT"]
    returned = bool(latest_is_present and len(prior_absent) >= max(1, int(min_prior_absent_events)))
    last_absent = prior_absent[-1] if prior_absent else None

    blockers = []
    if not latest_is_present:
        blockers.append("NO_EXPLICIT_CURRENT_PRESENCE")
    if len(prior_absent) < max(1, int(min_prior_absent_events)):
        blockers.append("NO_EXPLICIT_PRIOR_ABSENCE_RUN")

    return {
        "version": "PBK_RETURN_EVENT_FOUNDATION_V1",
        "player_id": str(player_id),
        "team_id": str(team_id),
        "before_utc": before_utc,
        "return_event": returned,
        "current_state": latest_state,
        "current_observed_at_utc": latest.get("observed_at_utc") if latest else None,
        "prior_absent_events": len(prior_absent),
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
    """Measure membership turnover and XI quality delta without causal claims."""
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
    quality_ready = (
        current_quality is not None
        and previous_quality is not None
        and current_covered >= minimum_quality_coverage
        and previous_covered >= minimum_quality_coverage
    )
    delta = round(current_quality - previous_quality, 3) if quality_ready else None

    blockers = []
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
        "changed_starters": len(changed_in) if len(current_ids) == 11 and len(previous_ids) == 11 else None,
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
