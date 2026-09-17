#!/usr/bin/env python3
"""Stage87 — normalized Team Style dimension evidence."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"
CONFIG = ROOT / "config" / "pbk_team_style_dimensions_v1.json"

SOURCE = OPS / "team_style_normalized_observations.jsonl"
OUT = OPS / "team_style_dimension_evidence.jsonl"
META = OPS / "stage87_team_style_dimensions_last_run.json"

VERSION = "PBK_STAGE87_NORMALIZED_STYLE_DIMENSION_EVIDENCE_V1"

SUPPORTED_DIMENSIONS = {
    "ATTACK_VOLUME",
    "POSSESSION_CONTROL",
    "DEFENSIVE_RESISTANCE",
}


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()

            if not text:
                continue

            payload = json.loads(text)

            if not isinstance(payload, dict):
                raise ValueError(
                    f"{path}:{line_number}: JSONL row must be an object"
                )

            rows.append(payload)

    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )


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


def observation_group_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("league_id") or ""),
        str(row.get("season") or ""),
        str(row.get("team_id") or ""),
        str(row.get("split") or "").lower(),
        str(row.get("window") or ""),
        str(row.get("profile_before_utc") or ""),
    )


def normalized_metric_known(row: dict[str, Any]) -> bool:
    if str(row.get("normalization_status") or "").upper() != "NORMALIZED":
        return False

    return (
        row.get("percentile") is not None
        and row.get("z_score") is not None
    )


def load_candidate_dimensions() -> list[dict[str, Any]]:
    payload = read_json(CONFIG)

    dimensions = []

    for dimension in payload.get("dimensions", []):
        if str(dimension.get("id") or "") not in SUPPORTED_DIMENSIONS:
            continue

        if str(dimension.get("status") or "") != "CANDIDATE":
            continue

        dimensions.append(dimension)

    return dimensions


def build_dimension_evidence(
    source_rows: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[str, ...],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in source_rows:
        key = observation_group_key(row)

        if not all(key):
            continue

        grouped[key].append(row)

    results: list[dict[str, Any]] = []

    for key, rows in grouped.items():
        metric_rows = {
            str(row.get("metric") or ""): row
            for row in rows
            if str(row.get("metric") or "")
        }

        (
            league_id,
            season,
            team_id,
            split,
            window,
            profile_before_utc,
        ) = key

        league_name = next(
            (
                row.get("league_name")
                for row in rows
                if row.get("league_name")
            ),
            None,
        )

        for dimension in dimensions:
            components = []
            known_components = 0

            for component in dimension.get("components", []):
                metric = str(component.get("metric") or "")
                direction = str(component.get("direction") or "")
                availability = str(
                    component.get("availability") or "REQUIRED"
                )

                metric_row = metric_rows.get(metric)
                known = (
                    metric_row is not None
                    and normalized_metric_known(metric_row)
                )

                if known:
                    known_components += 1

                components.append(
                    {
                        "metric": metric,
                        "direction": direction,
                        "availability": availability,
                        "known": known,
                        "normalization_status": (
                            metric_row.get("normalization_status")
                            if metric_row
                            else "MISSING"
                        ),
                        "raw_value": (
                            metric_row.get("raw_value")
                            if metric_row
                            else None
                        ),
                        "population_n": (
                            metric_row.get("population_n")
                            if metric_row
                            else None
                        ),
                        "percentile": (
                            metric_row.get("percentile")
                            if known
                            else None
                        ),
                        "z_score": (
                            metric_row.get("z_score")
                            if known
                            else None
                        ),
                    }
                )

            minimum_known = int(
                dimension.get("minimum_known_components") or 0
            )

            if known_components >= minimum_known:
                status = "READY_FOR_VALIDATION"
            else:
                status = "INSUFFICIENT_NORMALIZED_COMPONENTS"

            observed_at_values = sorted(
                str(row.get("observed_at_utc"))
                for row in rows
                if row.get("observed_at_utc")
            )

            results.append(
                {
                    "version": VERSION,
                    "source_version": (
                        "PBK_STAGE86_OPERATIONAL_NORMALIZED_STYLE_METRICS_V1"
                    ),
                    "dimension_spec_version": (
                        "PBK_TEAM_STYLE_DIMENSIONS_V1"
                    ),
                    "league_id": league_id,
                    "league_name": league_name,
                    "season": season,
                    "team_id": team_id,
                    "split": split,
                    "window": window,
                    "profile_before_utc": profile_before_utc,
                    "observed_at_utc": (
                        observed_at_values[-1]
                        if observed_at_values
                        else None
                    ),
                    "dimension": dimension.get("id"),
                    "dimension_status": status,
                    "known_components": known_components,
                    "minimum_known_components": minimum_known,
                    "components": components,
                    "dimension_value": None,
                    "aggregation_performed": False,
                    "arbitrary_weights_used": False,
                    "zero_to_ten_score": False,
                    "validation_required": True,
                    "research_only": True,
                    "provider_calls_added": 0,
                    "probability_mutation": False,
                    "eligibility_mutation": False,
                    "creates_signal": False,
                    "stake_changes": False,
                    "forward_journal_mutation": False,
                    "r1_r2_r3_mutation": False,
                    "ui_changes": False,
                    "api_changes": False,
                }
            )

    return sorted(
        results,
        key=lambda row: (
            str(row.get("league_id") or ""),
            str(row.get("season") or ""),
            str(row.get("team_id") or ""),
            str(row.get("split") or ""),
            str(row.get("window") or ""),
            str(row.get("profile_before_utc") or ""),
            str(row.get("dimension") or ""),
        ),
    )


def main() -> int:
    run_at = utc_now()
    source_rows = read_jsonl(SOURCE)

    if not source_rows:
        write_json(
            META,
            {
                "version": VERSION,
                "run_at_utc": run_at,
                "status": "WAITING_FOR_STAGE86_NORMALIZED_OBSERVATIONS",
                "source_rows": 0,
                "dimension_rows": 0,
                "provider_calls_added": 0,
                "research_only": True,
            },
        )

        print("WAITING_FOR_STAGE86_NORMALIZED_OBSERVATIONS")
        return 0

    dimensions = load_candidate_dimensions()

    rows = build_dimension_evidence(
        source_rows,
        dimensions,
    )

    write_jsonl(OUT, rows)

    ready = sum(
        1
        for row in rows
        if row.get("dimension_status") == "READY_FOR_VALIDATION"
    )

    insufficient = sum(
        1
        for row in rows
        if row.get("dimension_status")
        == "INSUFFICIENT_NORMALIZED_COMPONENTS"
    )

    write_json(
        META,
        {
            "version": VERSION,
            "run_at_utc": run_at,
            "status": "BUILT_DIMENSION_EVIDENCE",
            "source_rows": len(source_rows),
            "dimension_rows": len(rows),
            "ready_for_validation": ready,
            "insufficient_normalized_components": insufficient,
            "supported_dimensions": sorted(SUPPORTED_DIMENSIONS),
            "aggregation_performed": False,
            "arbitrary_weights_used": False,
            "provider_calls_added": 0,
            "research_only": True,
            "probability_mutation": False,
            "eligibility_mutation": False,
            "creates_signal": False,
            "stake_changes": False,
            "forward_journal_mutation": False,
            "r1_r2_r3_mutation": False,
            "ui_changes": False,
            "api_changes": False,
        },
    )

    print(
        json.dumps(
            {
                "status": "BUILT_DIMENSION_EVIDENCE",
                "source_rows": len(source_rows),
                "dimension_rows": len(rows),
                "ready_for_validation": ready,
                "insufficient": insufficient,
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
