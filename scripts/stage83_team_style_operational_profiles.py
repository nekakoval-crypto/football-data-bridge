#!/usr/bin/env python3
"""Stage83 — provider-free Team Style operational profile materialization.

Consumes Stage82 operational Team Style evidence and materializes rolling
Team Style profiles using the existing PBK_TEAM_STYLE_PROFILE_V1 foundation.

Governance:
- provider-free
- strict no-lookahead
- UNKNOWN remains UNKNOWN; no zero fill
- raw descriptive metrics only
- no style score
- no calibrated style dimensions
- no Matchup Grade
- no probability/value/signal/stake mutation
- no R1/R2/R3 mutation
- no Forward Journal mutation
- no UI/API mutation
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.pbk_team_style_profiles import (
        DEFAULT_WINDOWS,
        build_team_style_profile,
    )
except ModuleNotFoundError:
    from pbk_team_style_profiles import (
        DEFAULT_WINDOWS,
        build_team_style_profile,
    )


OPS = Path(os.getenv("OPS_DIR", "ops"))

SOURCE_EVIDENCE = OPS / "team_style_operational_evidence.jsonl"
OUT = OPS / "team_style_operational_profiles.json"
META = OPS / "stage83_team_style_profiles_last_run.json"

VERSION = "PBK_STAGE83_TEAM_STYLE_OPERATIONAL_PROFILES_V1"
SOURCE_VERSION = "PBK_STAGE82_TEAM_STYLE_OPERATIONAL_BRIDGE_V1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
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
                rows.append(item)

    return rows


def _team_key(row: dict[str, Any]) -> str:
    return str(row.get("team_id") or "").strip()


def _team_name(row: dict[str, Any]) -> str:
    return str(row.get("team_name") or "").strip()


def group_team_rows(
    evidence_rows: Iterable[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    exclusions = {
        "missing_team_id": 0,
        "missing_source": 0,
        "missing_or_naive_observed_at": 0,
        "missing_or_naive_kickoff": 0,
        "unknown_venue": 0,
    }

    for original in evidence_rows:
        row = dict(original or {})

        team_id = _team_key(row)
        if not team_id:
            exclusions["missing_team_id"] += 1
            continue

        source = str(row.get("source") or "").strip()
        if not source:
            exclusions["missing_source"] += 1
            continue

        if parse_iso(row.get("observed_at_utc")) is None:
            exclusions["missing_or_naive_observed_at"] += 1
            continue

        if parse_iso(row.get("kickoff_utc")) is None:
            exclusions["missing_or_naive_kickoff"] += 1
            continue

        venue = str(row.get("venue") or "").strip().upper()
        if venue not in {"H", "HOME", "A", "AWAY"}:
            exclusions["unknown_venue"] += 1
            continue

        grouped[team_id].append(row)

    return dict(grouped), exclusions


def build_operational_profiles(
    evidence_rows: Iterable[dict[str, Any]],
    before_utc: str,
    *,
    windows: Iterable[int] = DEFAULT_WINDOWS,
) -> dict[str, Any]:
    cutoff = parse_iso(before_utc)
    if cutoff is None:
        raise ValueError("aware before_utc is required")

    normalized_windows = tuple(int(value) for value in windows)
    if not normalized_windows or any(value <= 0 for value in normalized_windows):
        raise ValueError("windows must contain positive integers")
    if len(set(normalized_windows)) != len(normalized_windows):
        raise ValueError("windows must be unique")

    rows = list(evidence_rows)
    grouped, grouping_exclusions = group_team_rows(rows)

    teams: dict[str, Any] = {}
    teams_with_evidence = 0
    total_eligible_matches = 0

    for team_id in sorted(grouped, key=lambda value: (not value.isdigit(), value)):
        team_rows = grouped[team_id]

        names = [
            _team_name(row)
            for row in team_rows
            if _team_name(row)
        ]
        team_name = names[-1] if names else None

        profile = build_team_style_profile(
            team_rows,
            before_utc,
            windows=normalized_windows,
        )

        eligible = int(profile.get("eligible_matches_total") or 0)
        if eligible > 0:
            teams_with_evidence += 1
            total_eligible_matches += eligible

        teams[team_id] = {
            "team_id": team_id,
            "team_name": team_name,
            "profile": profile,
        }

    return {
        "version": VERSION,
        "source_version": SOURCE_VERSION,
        "source": "PBK_STAGE82_TEAM_STYLE_OPERATIONAL_EVIDENCE",
        "before_utc": cutoff.isoformat(),
        "windows": list(normalized_windows),
        "source_evidence_rows": len(rows),
        "teams_seen": len(grouped),
        "teams_with_eligible_evidence": teams_with_evidence,
        "total_eligible_team_matches": total_eligible_matches,
        "grouping_exclusions": grouping_exclusions,
        "teams": teams,
        "provider_calls_added": 0,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "raw_components_only": True,
        "style_scale_calibrated": False,
        "formation_is_style": False,
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "r1_r2_r3_mutation": False,
        "ui_changes": False,
        "api_changes": False,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    before_utc = utc_now_iso()
    evidence_rows = read_jsonl(SOURCE_EVIDENCE)

    if not evidence_rows:
        result = {
            "version": VERSION,
            "status": "WAITING_FOR_STAGE82_EVIDENCE",
            "source_evidence_rows": 0,
            "teams_seen": 0,
            "teams_with_eligible_evidence": 0,
            "profiles_written": 0,
            "output_path": str(OUT),
            "provider_calls_added": 0,
            "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
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
        write_json(META, result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    materialized = build_operational_profiles(
        evidence_rows,
        before_utc,
        windows=DEFAULT_WINDOWS,
    )

    write_json(OUT, materialized)

    teams = materialized.get("teams") or {}
    eligible = int(materialized.get("teams_with_eligible_evidence") or 0)

    status = "READY" if eligible > 0 else "ATTENTION"

    result = {
        "version": VERSION,
        "status": status,
        "before_utc": materialized["before_utc"],
        "source_evidence_rows": materialized["source_evidence_rows"],
        "teams_seen": materialized["teams_seen"],
        "teams_with_eligible_evidence": eligible,
        "profiles_written": len(teams),
        "total_eligible_team_matches": materialized["total_eligible_team_matches"],
        "grouping_exclusions": materialized["grouping_exclusions"],
        "output_path": str(OUT),
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

    write_json(META, result)

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
