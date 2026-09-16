#!/usr/bin/env python3
"""Validate PBK Brain Grade Readiness registry.

Governance-only. This script performs no provider calls and does not mutate any
betting, probability, eligibility, stake, settlement or forward-journal state.
"""
from __future__ import annotations

import json
from pathlib import Path

REGISTRY = Path("config/pbk_grade_readiness.json")
REQUIRED_IDS = {
    "PLAYER_OVERALL_GRADE",
    "PLAYER_FORM_GRADE",
    "XI_QUALITY",
    "PLAYER_IMPORTANCE",
    "ROTATION_COUNT",
    "ROTATION_QUALITY_IMPACT",
    "ABSENCE_IMPACT",
    "RETURN_IMPACT",
    "TEAM_COMPONENT_GRADES",
    "TEAM_OVERALL_GRADE",
    "MATCHUP_GRADE",
}


def validate(payload: dict) -> list[str]:
    errors: list[str] = []
    allowed = set(payload.get("allowed_statuses") or [])
    metrics = payload.get("metrics") or []
    by_id = {row.get("id"): row for row in metrics if row.get("id")}

    missing = sorted(REQUIRED_IDS - set(by_id))
    if missing:
        errors.append(f"missing required metric ids: {', '.join(missing)}")
    if len(by_id) != len(metrics):
        errors.append("metric ids must be non-empty and unique")

    for metric_id, row in sorted(by_id.items()):
        status = row.get("status")
        if status not in allowed:
            errors.append(f"{metric_id}: unsupported status {status!r}")
        if not row.get("reason"):
            errors.append(f"{metric_id}: reason is required")
        if not row.get("next_gate"):
            errors.append(f"{metric_id}: next_gate is required")
        if status == "VALIDATED" and not row.get("validation_evidence"):
            errors.append(f"{metric_id}: VALIDATED requires validation_evidence")
        if status == "DATA_BLOCKED" and row.get("production_evidence_required") is not True:
            errors.append(f"{metric_id}: DATA_BLOCKED must declare production_evidence_required=true")
        if status == "NOT_IMPLEMENTED" and row.get("code_ready") is True:
            errors.append(f"{metric_id}: NOT_IMPLEMENTED cannot have code_ready=true")

    overall = by_id.get("PLAYER_OVERALL_GRADE", {})
    components = overall.get("components") or {}
    if components.get("progression") != "PROXY_LIMITED":
        errors.append("PLAYER_OVERALL_GRADE: progression must remain explicitly PROXY_LIMITED")
    if components.get("pressing") != "UNAVAILABLE_IN_AGGREGATE_SOURCE":
        errors.append("PLAYER_OVERALL_GRADE: pressing must remain explicitly unavailable for aggregate source")

    form = by_id.get("PLAYER_FORM_GRADE", {})
    form_components = form.get("components") or {}
    for required in ("last", "form_3", "form_5", "form_10", "season"):
        if required not in form_components:
            errors.append(f"PLAYER_FORM_GRADE: missing {required} component")

    team_components = by_id.get("TEAM_COMPONENT_GRADES", {})
    component_map = team_components.get("components") or {}
    required_team_components = {
        "attack", "defence", "form", "home", "away", "schedule_fatigue",
        "squad", "xi_quality", "availability", "motivation", "market",
    }
    missing_team = sorted(required_team_components - set(component_map))
    if missing_team:
        errors.append(f"TEAM_COMPONENT_GRADES: missing components {', '.join(missing_team)}")

    for metric_id in ("ABSENCE_IMPACT", "RETURN_IMPACT", "ROTATION_QUALITY_IMPACT"):
        row = by_id.get(metric_id, {})
        if row.get("code_ready") is not True:
            errors.append(f"{metric_id}: research foundation must remain code_ready=true")
        if row.get("status") not in {"DATA_BLOCKED", "VALIDATION_PENDING", "PROXY_LIMITED"}:
            errors.append(f"{metric_id}: cannot be promoted before evidence and validation")

    absence_components = by_id.get("ABSENCE_IMPACT", {}).get("components") or {}
    if absence_components.get("total_impact") != "FORBIDDEN_UNTIL_WEIGHTING_VALIDATED":
        errors.append("ABSENCE_IMPACT: total impact must remain forbidden until weighting validation")
    return_components = by_id.get("RETURN_IMPACT", {}).get("components") or {}
    if return_components.get("return_impact_score") != "NOT_AUTHORIZED":
        errors.append("RETURN_IMPACT: return impact score must remain unauthorized")

    team_overall = by_id.get("TEAM_OVERALL_GRADE", {})
    if team_overall.get("status") != "NOT_IMPLEMENTED" or team_overall.get("code_ready") is not False:
        errors.append("TEAM_OVERALL_GRADE must remain NOT_IMPLEMENTED until component weighting is validated")

    matchup = by_id.get("MATCHUP_GRADE", {})
    matchup_components = matchup.get("components") or {}
    if matchup.get("code_ready") is not True:
        errors.append("MATCHUP_GRADE: research foundation must remain code_ready=true")
    if matchup.get("status") not in {"DATA_BLOCKED", "VALIDATION_PENDING", "PROXY_LIMITED"}:
        errors.append("MATCHUP_GRADE: cannot be promoted before style evidence and OOS validation")
    if matchup_components.get("formation") != "CONTEXT_ONLY_NOT_STYLE":
        errors.append("MATCHUP_GRADE: formation must remain context-only, not a style feature")
    if matchup_components.get("overall_matchup_grade") != "NOT_AUTHORIZED":
        errors.append("MATCHUP_GRADE: overall matchup grade must remain unauthorized")
    for required in (
        "press_vs_buildup",
        "transition_vs_transition_defence",
        "width_vs_wide_defence",
        "aerial_vs_aerial_defence",
        "set_piece_vs_set_piece_defence",
        "low_block_breaking_vs_low_block_defence",
        "central_progression_vs_central_compactness",
    ):
        if required not in matchup_components:
            errors.append(f"MATCHUP_GRADE: missing {required} component")

    for metric_id in (
        "PLAYER_OVERALL_GRADE",
        "XI_QUALITY",
        "PLAYER_IMPORTANCE",
        "TEAM_COMPONENT_GRADES",
        "MATCHUP_GRADE",
    ):
        if by_id.get(metric_id, {}).get("status") == "VALIDATED":
            errors.append(f"{metric_id}: cannot be pre-marked VALIDATED by governance registry")

    return errors


def main() -> int:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: PBK grade readiness registry ({len(payload.get('metrics') or [])} metrics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
