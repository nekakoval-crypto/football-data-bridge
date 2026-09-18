#!/usr/bin/env python3
"""Stage95 — explicit validation gate for PBK style-vs-style matchup."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from pbk_matchup_style import MATCHUP_COMPONENTS
except ModuleNotFoundError:
    from scripts.pbk_matchup_style import MATCHUP_COMPONENTS


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"

SOURCE = OPS / "team_style_dimension_validation_statistics.json"
OUT = OPS / "matchup_validation_gate.json"
META = OPS / "stage95_matchup_validation_gate_last_run.json"

VERSION = "PBK_STAGE95_MATCHUP_VALIDATION_GATE_V1"
SOURCE_VERSION = "PBK_STAGE94_STYLE_DIMENSION_VALIDATION_STATISTICS_V1"


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(path: Path) -> Any:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


def validation_evidence_dimensions(
    payload: Any,
) -> set[str]:
    if not isinstance(payload, dict):
        return set()

    if str(payload.get("version") or "") != SOURCE_VERSION:
        return set()

    result = set()

    for row in payload.get("groups") or []:
        if (
            str(row.get("validation_status") or "")
            == "VALIDATION_EVIDENCE_AVAILABLE"
        ):
            dimension = str(
                row.get("dimension") or ""
            ).strip()

            if dimension:
                result.add(dimension)

    return result


def build_gate(payload: Any) -> dict[str, Any]:
    evidence_dimensions = validation_evidence_dimensions(
        payload
    )

    threshold_policy_defined = bool(
        isinstance(payload, dict)
        and payload.get(
            "validation_threshold_policy_defined"
        )
    )

    components = {}

    for component, (
        acting_dimension,
        opponent_dimension,
    ) in MATCHUP_COMPONENTS.items():

        acting_evidence = (
            acting_dimension in evidence_dimensions
        )
        opponent_evidence = (
            opponent_dimension in evidence_dimensions
        )

        if not acting_evidence or not opponent_evidence:
            status = "DATA_BLOCKED"
        elif not threshold_policy_defined:
            status = "VALIDATION_POLICY_PENDING"
        else:
            status = "EVIDENCE_AVAILABLE_NOT_AUTHORIZED"

        components[component] = {
            "acting_dimension": acting_dimension,
            "opponent_dimension": opponent_dimension,
            "acting_validation_evidence_available": (
                acting_evidence
            ),
            "opponent_validation_evidence_available": (
                opponent_evidence
            ),
            "status": status,
            "matchup_effect_claim_authorized": False,
            "component_weight_authorized": False,
        }

    evidence_ready = sum(
        1
        for row in components.values()
        if (
            row[
                "acting_validation_evidence_available"
            ]
            and row[
                "opponent_validation_evidence_available"
            ]
        )
    )

    return {
        "version": VERSION,
        "source_version": SOURCE_VERSION,
        "status": "DATA_BLOCKED",
        "validated_style_dimensions_available": sorted(
            evidence_dimensions
        ),
        "validation_threshold_policy_defined": (
            threshold_policy_defined
        ),
        "components": components,
        "components_with_required_evidence": (
            evidence_ready
        ),
        "total_components": len(MATCHUP_COMPONENTS),
        "matchup_grade_authorized": False,
        "overall_edge_authorized": False,
        "component_weights_authorized": False,
        "winner_claim_authorized": False,
        "passport_context_allowed": True,
        "validated_matchup_claim_allowed": False,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "research_only": True,
        "no_lookahead": True,
        "provider_calls_added": 0,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "creates_signal": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "r1_r2_r3_mutation": False,
        "ui_decision_mutation": False,
    }


def main() -> int:
    run_at = utc_now()

    source = read_json(SOURCE)
    gate = build_gate(source)
    gate["run_at_utc"] = run_at

    write_json(OUT, gate)

    write_json(
        META,
        {
            "version": VERSION,
            "run_at_utc": run_at,
            "status": gate["status"],
            "components_with_required_evidence": (
                gate[
                    "components_with_required_evidence"
                ]
            ),
            "total_components": gate["total_components"],
            "output": str(OUT.relative_to(ROOT)),
            "research_only": True,
            "probability_mutation": False,
            "eligibility_mutation": False,
            "creates_signal": False,
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
