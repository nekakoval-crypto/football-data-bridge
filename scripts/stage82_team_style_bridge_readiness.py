#!/usr/bin/env python3
"""Stage82 readiness/coverage audit for Team Style operational evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from scripts.stage82_team_style_operational_bridge import (
        SOURCE_LEDGER,
        OUT,
        fixture_pairs,
        read_csv,
        build_evidence,
    )
except ModuleNotFoundError:
    from stage82_team_style_operational_bridge import (
        SOURCE_LEDGER,
        OUT,
        fixture_pairs,
        read_csv,
        build_evidence,
    )

OPS = Path(os.getenv("OPS_DIR", "ops"))
META = OPS / "stage82_team_style_bridge_readiness.json"

VERSION = "PBK_STAGE82_TEAM_STYLE_BRIDGE_READINESS_V1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows = []
    with path.open(encoding="utf-8") as stream:
        for raw in stream:
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)

    return rows


def evidence_key(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("fixture_id") or "").strip(),
        str(row.get("team_id") or "").strip(),
    )


def audit_readiness(
    source_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    pairs, pair_exclusions = fixture_pairs(source_rows)
    built_rows, build_meta = build_evidence(source_rows)

    expected_keys = {
        evidence_key(row)
        for row in built_rows
        if all(evidence_key(row))
    }

    actual_keys = {
        evidence_key(row)
        for row in evidence_rows
        if str(row.get("source") or "").strip()
        == "PBK_STAGE81_TEAM_MATCH_STATISTICS"
        and all(evidence_key(row))
    }

    missing_keys = sorted(expected_keys - actual_keys)
    unexpected_keys = sorted(actual_keys - expected_keys)

    if not source_rows:
        status = "WAITING_FOR_STAGE81_DATA"
    elif not expected_keys:
        status = "ATTENTION"
    elif missing_keys:
        status = "PARTIAL"
    else:
        status = "READY"

    return {
        "version": VERSION,
        "status": status,
        "source_rows": len(source_rows),
        "complete_fixture_pairs": len(pairs),
        "expected_evidence_rows": len(expected_keys),
        "actual_operational_evidence_rows": len(actual_keys),
        "missing_evidence_rows": len(missing_keys),
        "unexpected_evidence_rows": len(unexpected_keys),
        "missing_fixture_team_keys": [
            {"fixture_id": fixture_id, "team_id": team_id}
            for fixture_id, team_id in missing_keys
        ],
        "unexpected_fixture_team_keys": [
            {"fixture_id": fixture_id, "team_id": team_id}
            for fixture_id, team_id in unexpected_keys
        ],
        "fixture_pair_exclusions": pair_exclusions,
        "bridge_validation": build_meta.get("validation", {}),
        "coverage_pct": (
            round(100.0 * len(actual_keys & expected_keys) / len(expected_keys), 2)
            if expected_keys
            else 0.0
        ),
        "provider_calls_added": 0,
        "missing_policy": "UNKNOWN_NOT_ZERO",
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "ui_changes": False,
    }


def main() -> int:
    source_rows = read_csv(SOURCE_LEDGER)
    evidence_rows = read_jsonl(OUT)

    result = audit_readiness(source_rows, evidence_rows)

    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
