#!/usr/bin/env python3
"""Stage83 Team Style operational profile readiness audit."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

OPS = Path(os.getenv("OPS_DIR", "ops"))

SOURCE_EVIDENCE = OPS / "team_style_operational_evidence.jsonl"
PROFILES = OPS / "team_style_operational_profiles.json"
OUT = OPS / "stage83_team_style_profiles_readiness.json"

VERSION = "PBK_STAGE83_TEAM_STYLE_PROFILES_READINESS_V1"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0

    count = 0
    with path.open(encoding="utf-8-sig") as stream:
        for raw in stream:
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                count += 1

    return count


def build_readiness(
    *,
    source_evidence_rows: int,
    profiles_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if source_evidence_rows <= 0:
        status = "WAITING_FOR_STAGE82_EVIDENCE"
        teams_seen = 0
        teams_with_eligible_evidence = 0
        total_eligible_team_matches = 0
        profile_version = None
        before_utc = None

    elif not profiles_payload:
        status = "PARTIAL"
        teams_seen = 0
        teams_with_eligible_evidence = 0
        total_eligible_team_matches = 0
        profile_version = None
        before_utc = None

    else:
        teams_seen = int(profiles_payload.get("teams_seen") or 0)
        teams_with_eligible_evidence = int(
            profiles_payload.get("teams_with_eligible_evidence") or 0
        )
        total_eligible_team_matches = int(
            profiles_payload.get("total_eligible_team_matches") or 0
        )
        profile_version = profiles_payload.get("version")
        before_utc = profiles_payload.get("before_utc")

        if teams_seen <= 0:
            status = "ATTENTION"
        elif teams_with_eligible_evidence <= 0:
            status = "ATTENTION"
        elif teams_with_eligible_evidence < teams_seen:
            status = "PARTIAL"
        else:
            status = "READY"

    coverage_pct = (
        round(100.0 * teams_with_eligible_evidence / teams_seen, 2)
        if teams_seen
        else 0.0
    )

    return {
        "version": VERSION,
        "status": status,
        "source_evidence_rows": source_evidence_rows,
        "profiles_present": bool(profiles_payload),
        "profile_version": profile_version,
        "before_utc": before_utc,
        "teams_seen": teams_seen,
        "teams_with_eligible_evidence": teams_with_eligible_evidence,
        "team_profile_coverage_pct": coverage_pct,
        "total_eligible_team_matches": total_eligible_team_matches,
        "provider_calls_added": 0,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "raw_components_only": True,
        "style_scale_calibrated": False,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "r1_r2_r3_mutation": False,
        "ui_changes": False,
        "api_changes": False,
    }


def main() -> int:
    source_rows = count_jsonl_rows(SOURCE_EVIDENCE)
    profiles = read_json(PROFILES)

    result = build_readiness(
        source_evidence_rows=source_rows,
        profiles_payload=profiles,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
