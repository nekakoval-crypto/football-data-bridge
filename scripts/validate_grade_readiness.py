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

    for metric_id in ("PLAYER_OVERALL_GRADE", "XI_QUALITY", "PLAYER_IMPORTANCE"):
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
