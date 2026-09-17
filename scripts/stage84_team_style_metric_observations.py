#!/usr/bin/env python3
"""Stage84 operational materialization of Team Style metric observations.

Consumes Stage83 operational Team Style profiles and emits a flat,
provider-free research dataset for empirical normalization.

No betting, probability, value, stake, signal, R1/R2/R3, Forward Journal,
UI or API mutations are performed here.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OPS = Path(os.getenv("OPS_DIR", "ops"))

SOURCE = OPS / "team_style_operational_profiles.json"
OUT = OPS / "team_style_metric_observations.jsonl"
META = OPS / "stage84_team_style_metric_observations_last_run.json"

VERSION = "PBK_STAGE84_TEAM_STYLE_METRIC_OBSERVATIONS_V1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def flatten_profiles(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    before_utc = payload.get("before_utc")
    teams = payload.get("teams")

    if not isinstance(teams, dict):
        return rows

    for team_id, team_entry in teams.items():
        if not isinstance(team_entry, dict):
            continue

        profile = team_entry.get("profile")
        if not isinstance(profile, dict):
            continue

        team_name = team_entry.get("team_name") or profile.get("team_name")
        league_id = team_entry.get("league_id") or profile.get("league_id")
        league_name = team_entry.get("league_name") or profile.get("league_name")
        season = team_entry.get("season") or profile.get("season")

        splits = profile.get("splits")
        if not isinstance(splits, dict):
            continue

        for split_name, split_payload in splits.items():
            if not isinstance(split_payload, dict):
                continue

            windows = split_payload.get("windows")
            if not isinstance(windows, dict):
                continue

            for window_name, window_payload in windows.items():
                if not isinstance(window_payload, dict):
                    continue

                try:
                    window = int(window_name)
                except (TypeError, ValueError):
                    continue

                metrics = window_payload.get("metrics")
                if not isinstance(metrics, dict):
                    continue

                for metric_name, metric_payload in metrics.items():
                    if not isinstance(metric_payload, dict):
                        continue

                    status = metric_payload.get("status")
                    mean = metric_payload.get("mean")

                    row = {
                        "schema_version": VERSION,
                        "source": "PBK_STAGE83_TEAM_STYLE_OPERATIONAL_PROFILES",
                        "source_profile_version": payload.get("version"),
                        "profile_before_utc": before_utc,
                        "observed_at_utc": before_utc,
                        "team_id": str(team_id),
                        "team_name": team_name,
                        "league_id": str(league_id) if league_id is not None else None,
                        "league_name": (
                            str(league_name) if league_name is not None else None
                        ),
                        "season": str(season) if season is not None else None,
                        "split": str(split_name).lower(),
                        "window": window,
                        "metric": str(metric_name),
                        "value": mean if status == "KNOWN" else None,
                        "metric_status": status,
                        "sample_size": metric_payload.get("sample_size"),
                        "coverage": metric_payload.get("coverage"),
                        "window_actual_matches": window_payload.get("actual_matches"),
                        "window_complete": window_payload.get("window_complete"),
                        "style_dimension_value": None,
                    }

                    rows.append(row)

    rows.sort(
        key=lambda row: (
            str(row.get("league_id") or ""),
            str(row.get("season") or ""),
            str(row.get("team_id") or ""),
            str(row.get("split") or ""),
            int(row.get("window") or 0),
            str(row.get("metric") or ""),
        )
    )

    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )

    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    payload = read_json(SOURCE)

    if not payload:
        result = {
            "version": VERSION,
            "status": "WAITING_FOR_STAGE83_PROFILES",
            "source_path": str(SOURCE),
            "output_path": str(OUT),
            "rows_written": 0,
            "provider_calls_added": 0,
            "research_only": True,
            "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
            "style_dimension_value": None,
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

    rows = flatten_profiles(payload)
    write_jsonl(OUT, rows)

    result = {
        "version": VERSION,
        "status": "READY" if rows else "ATTENTION",
        "source_path": str(SOURCE),
        "output_path": str(OUT),
        "source_profile_version": payload.get("version"),
        "profile_before_utc": payload.get("before_utc"),
        "rows_written": len(rows),
        "provider_calls_added": 0,
        "research_only": True,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "style_dimension_value": None,
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
