#!/usr/bin/env python3
"""Stage82 — provider-free Stage81 -> Team Style operational evidence bridge.

Consumes the durable Stage81 team-match statistics ledger and converts complete
HOME/AWAY fixture pairs into PBK_TEAM_STYLE_EVIDENCE_V1-compatible rows.

Research/data layer only:
- zero provider calls
- strict explicit fixture/team/venue provenance
- missing metrics remain UNKNOWN (absent), never zero-filled
- one evidence row per fixture + team
- opponent metrics provide explicit *_against fields
- no style score, matchup grade, probability/value/signal/stake mutation
"""

from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.pbk_team_style_evidence import (
        EVIDENCE_VERSION,
        append_evidence,
        normalized_import_row,
    )
except ModuleNotFoundError:
    from pbk_team_style_evidence import (
        EVIDENCE_VERSION,
        append_evidence,
        normalized_import_row,
    )

OPS = Path(os.getenv("OPS_DIR", "ops"))

SOURCE_LEDGER = OPS / "team_match_statistics.csv"
OUT = OPS / "team_style_operational_evidence.jsonl"
META = OPS / "stage82_team_style_bridge_last_run.json"

SOURCE_NAME = "PBK_STAGE81_TEAM_MATCH_STATISTICS"
VERSION = "PBK_STAGE82_TEAM_STYLE_OPERATIONAL_BRIDGE_V1"


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def number(value: Any) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("%"):
        raw = raw[:-1].strip()
    try:
        result = float(raw)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


FORWARD_MAP = {
    "shots_total": "shots_for",
    "shots_on_goal": "shots_on_target_for",
    "possession_pct": "possession_pct",
    "corners": "corners_for",
    "passes_total": "passes",
    "passes_accuracy_pct": "pass_accuracy_pct",
    "expected_goals": "xg_for",
}

AGAINST_MAP = {
    "shots_total": "shots_against",
    "shots_on_goal": "shots_on_target_against",
    "corners": "corners_against",
    "expected_goals": "xg_against",
}


def metrics_from_pair(
    row: dict[str, Any],
    opponent: dict[str, Any],
) -> dict[str, float]:
    metrics: dict[str, float] = {}

    for source_field, target_field in FORWARD_MAP.items():
        value = number(row.get(source_field))
        if value is not None:
            metrics[target_field] = value

    for source_field, target_field in AGAINST_MAP.items():
        value = number(opponent.get(source_field))
        if value is not None:
            metrics[target_field] = value

    return metrics


def fixture_pairs(
    rows: list[dict[str, Any]],
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, int]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    exclusions = {
        "missing_fixture_id": 0,
        "unknown_side": 0,
        "duplicate_side": 0,
        "incomplete_fixture_pair": 0,
    }

    for row in rows:
        fixture_id = str(row.get("fixture_id") or "").strip()
        if not fixture_id:
            exclusions["missing_fixture_id"] += 1
            continue

        side = str(row.get("side") or "").strip().upper()
        if side not in {"HOME", "AWAY"}:
            exclusions["unknown_side"] += 1
            continue

        slot = grouped.setdefault(fixture_id, {})
        if side in slot:
            exclusions["duplicate_side"] += 1
            continue
        slot[side] = row

    pairs = []
    for fixture_id in sorted(grouped):
        sides = grouped[fixture_id]
        if set(sides) != {"HOME", "AWAY"}:
            exclusions["incomplete_fixture_pair"] += 1
            continue
        pairs.append((sides["HOME"], sides["AWAY"]))

    return pairs, exclusions


def build_evidence(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pairs, exclusions = fixture_pairs(rows)
    evidence: list[dict[str, Any]] = []

    validation = {
        "missing_team_id": 0,
        "invalid_kickoff": 0,
        "invalid_observed_at": 0,
        "normalized_rejected": 0,
    }

    for home, away in pairs:
        fixture_id = str(home.get("fixture_id") or "").strip()

        for row, opponent in ((home, away), (away, home)):
            team_id = str(row.get("team_id") or "").strip()
            opponent_id = str(opponent.get("team_id") or "").strip()

            if not team_id:
                validation["missing_team_id"] += 1
                continue

            kickoff = parse_iso(row.get("kickoff_utc"))
            if kickoff is None:
                validation["invalid_kickoff"] += 1
                continue

            observed = parse_iso(row.get("observed_at_utc"))
            if observed is None:
                validation["invalid_observed_at"] += 1
                continue

            source_observation_id = (
                f"stage81:{fixture_id}:{observed.isoformat()}"
            )

            normalized = normalized_import_row(
                {
                    "source": SOURCE_NAME,
                    "source_observation_id": source_observation_id,
                    "fixture_id": fixture_id,
                    "kickoff_utc": kickoff.isoformat(),
                    "observed_at_utc": observed.isoformat(),
                    "team_id": team_id,
                    "team_name": row.get("team_name"),
                    "opponent_team_id": opponent_id or None,
                    "opponent_team_name": opponent.get("team_name"),
                    "venue": row.get("side"),
                    "metrics": metrics_from_pair(row, opponent),
                }
            )

            if normalized is None:
                validation["normalized_rejected"] += 1
                continue

            normalized["schema_version"] = EVIDENCE_VERSION
            normalized["bridge_version"] = VERSION
            normalized["missing_evidence_policy"] = "UNKNOWN_NOT_ZERO"
            normalized["provider_calls_added"] = 0
            normalized["research_only"] = True
            normalized["creates_signal"] = False
            normalized["probability_mutation"] = False
            normalized["stake_changes"] = False

            evidence.append(normalized)

    return evidence, {
        "source_rows": len(rows),
        "complete_fixture_pairs": len(pairs),
        "fixture_exclusions": exclusions,
        "validation": validation,
        "evidence_rows_built": len(evidence),
    }


def main() -> int:
    rows = read_csv(SOURCE_LEDGER)

    if not rows:
        meta = {
            "version": VERSION,
            "status": "WAITING_FOR_STAGE81_DATA",
            "source": str(SOURCE_LEDGER),
            "source_rows": 0,
            "evidence_rows_built": 0,
            "rows_added": 0,
            "duplicates_skipped": 0,
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
    else:
        evidence, build_meta = build_evidence(rows)
        write_meta = append_evidence(evidence, OUT)

        meta = {
            "version": VERSION,
            "status": "READY" if evidence else "ATTENTION",
            "source": str(SOURCE_LEDGER),
            **build_meta,
            **write_meta,
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

    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(meta, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

