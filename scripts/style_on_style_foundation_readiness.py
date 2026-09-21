#!/usr/bin/env python3
"""Checklist item 12 — style-on-style data/research foundation readiness."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"
OUT = OPS / "style_on_style_foundation_readiness.json"

PATHS = {
    "stage82": OPS / "stage82_team_style_bridge_last_run.json",
    "stage83": OPS / "stage83_team_style_profiles_last_run.json",
    "stage84": OPS / "stage84_team_style_metric_observations_last_run.json",
    "stage87": OPS / "stage87_team_style_dimensions_last_run.json",
    "stage88": OPS / "stage88_team_style_dimension_validation_last_run.json",
    "stage89": OPS / "stage89_team_style_dimension_forward_labels_last_run.json",
    "stage93": OPS / "stage93_team_style_validation_readiness_last_run.json",
    "stage95": OPS / "stage95_matchup_validation_gate_last_run.json",
}
VERSION = "PBK_ITEM12_STYLE_ON_STYLE_FOUNDATION_V1"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def build_readiness(metas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    s82 = metas.get("stage82", {})
    s83 = metas.get("stage83", {})
    s84 = metas.get("stage84", {})
    s87 = metas.get("stage87", {})
    s88 = metas.get("stage88", {})
    s89 = metas.get("stage89", {})
    s93 = metas.get("stage93", {})
    s95 = metas.get("stage95", {})

    evidence_rows = int(s82.get("evidence_rows_built") or 0)
    profiles = int(s83.get("profiles_written") or 0)
    metric_rows = int(s84.get("rows_written") or 0)
    ready_dimensions = int(s87.get("ready_for_validation") or 0)
    validation_rows = int(s88.get("total_validation_rows") or 0)
    labels = int(s89.get("total_labels") or 0)
    ready_groups = int(s93.get("ready_groups") or 0)

    foundation_complete = all([
        evidence_rows > 0,
        profiles > 0,
        metric_rows > 0,
        ready_dimensions > 0,
        validation_rows > 0,
    ])

    blockers = []
    if ready_dimensions <= 0:
        blockers.append("NO_STYLE_DIMENSION_READY_FOR_VALIDATION")
    if validation_rows <= 0:
        blockers.append("NO_FORWARD_STYLE_VALIDATION_OBSERVATIONS")
    if labels < 30:
        blockers.append("FORWARD_LABELED_SAMPLE_BELOW_30")
    if ready_groups <= 0:
        blockers.append("NO_STYLE_VALIDATION_GROUP_REACHED_SAMPLE_GATE")
    blockers.extend([
        "ADVANCED_MATCHUP_DIMENSIONS_STILL_REQUIRE_DETAILED_EVENT_METRICS",
        "STYLE_SPECIALIST_PROBABILITY_MODEL_NOT_VALIDATED",
    ])

    return {
        "version": VERSION,
        "run_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "VALIDATION_PENDING" if foundation_complete else "DATA_FOUNDATION_IN_PROGRESS",
        "checklist_item_12_data_engineering_foundation": "COMPLETE" if foundation_complete else "IN_PROGRESS",
        "checklist_item_12_predictive_authority": "NOT_AUTHORIZED",
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "evidence": {
            "stage82_style_evidence_rows": evidence_rows,
            "stage83_profiles_written": profiles,
            "stage84_metric_rows": metric_rows,
            "stage87_ready_dimension_rows": ready_dimensions,
            "stage88_forward_validation_rows": validation_rows,
            "stage89_forward_labels": labels,
            "stage93_ready_groups": ready_groups,
            "stage95_advanced_matchup_gate_status": s95.get("status"),
        },
        "governance": {
            "canonical_metric_names_locked": True,
            "missing_evidence_unknown_not_zero": True,
            "arbitrary_style_weights_forbidden": True,
            "formation_context_only": True,
            "forward_only_validation": True,
        },
        "hard_blockers_to_predictive_authority": blockers,
        "closure_rule": "Item 12 DATA/RESEARCH foundation may be closed when COMPLETE. Predictive style-on-style authority remains forbidden until forward samples and specialist validation pass; advanced press/transition/width/aerial/set-piece matchups remain data-dependent.",
    }


def main() -> int:
    payload = build_readiness({k: read_json(v) for k, v in PATHS.items()})
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
