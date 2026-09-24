#!/usr/bin/env python3
"""PBK #272 — Environmental Stress V1 prospective research monitor.

Captures only the first valid PREMATCH_FROZEN environmental feature
observation per fixture. Missed fixtures cannot be reconstructed later.

Settlement uses only the existing exact-FT live overlay and is stored
separately from immutable prematch evidence.

Research-only. No signal, probability, eligibility, value or stake authority.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPS = Path(os.getenv("OPS_DIR", str(ROOT / "ops")))
DEFAULT_CONFIG = ROOT / "config" / "pbk_environmental_stress_v1_forward.json"

VERSION = "PBK_ENVIRONMENTAL_STRESS_FORWARD_MONITOR_V1"
EXPECTED_RESEARCH_ID = "PBK_ENVIRONMENTAL_STRESS_V1_FORWARD"
EXPECTED_FEATURE_VERSION = "PBK_ENVIRONMENTAL_STRESS_FEATURES_V1"

FACTOR_GROUP_FIELDS = {
    "THERMAL": "thermal_group_status",
    "WIND_GUST": "wind_group_status",
    "PRECIPITATION": "precipitation_group_status",
    "VISIBILITY_THUNDER": "visibility_thunder_group_status",
    "AIR_QUALITY": "air_quality_group_status",
    "ALTITUDE": "altitude_group_status",
    "SURFACE": "surface_group_status",
    "ROOF_EXPOSURE": "venue_environment_status",
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("config root must be object")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> tuple[bytes, list[dict[str, Any]]]:
    if not path.exists():
        return b"", []
    raw = path.read_bytes()
    rows = []
    for line in raw.decode("utf-8-sig").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path.name}: row must be object")
            rows.append(value)
    ids = [str(r.get("event_id") or "") for r in rows]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{path.name}: duplicate/invalid event_id")
    return raw, rows


def atomic_append(path: Path, original: bytes, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    sep = b"\n" if original and not original.endswith(b"\n") else b""
    addition = b"".join(
        (json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for r in rows
    )
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(original + sep + addition)
    os.replace(tmp, path)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def event_id(kind: str, fixture_id: str) -> str:
    return hashlib.sha256(f"{VERSION}|{kind}|{fixture_id}".encode("utf-8")).hexdigest()[:32]


def validate_contract(config: dict[str, Any]) -> None:
    if config.get("research_id") != EXPECTED_RESEARCH_ID:
        raise ValueError("research_id drift")
    if config.get("feature_version") != EXPECTED_FEATURE_VERSION:
        raise ValueError("feature_version drift")
    if config.get("status") != "FORWARD_EVIDENCE_ACCUMULATION":
        raise ValueError("status drift")
    if config.get("authority") != "RESEARCH":
        raise ValueError("authority drift")

    inputs = config.get("prospective_inputs") or {}
    for key in [
        "first_frozen_observation_only",
        "observation_must_precede_kickoff",
        "exact_ft_settlement_only",
    ]:
        if inputs.get(key) is not True:
            raise ValueError(f"{key} must remain true")
    if inputs.get("historical_backfill") is not False:
        raise ValueError("historical backfill must stay forbidden")

    if config.get("factor_groups") != list(FACTOR_GROUP_FIELDS):
        raise ValueError("factor-group contract drift")

    guards = config.get("guards") or {}
    for key in [
        "unknown_not_zero",
        "no_lookahead",
        "prematch_frozen_required",
        "postmatch_weather_forbidden",
        "historical_weather_backfill_forbidden",
        "aggregate_environment_score_forbidden",
        "double_counting_guard_required",
    ]:
        if guards.get(key) is not True:
            raise ValueError(f"guard drift: {key}")

    if guards.get("predictive_authority") != "NOT_AUTHORIZED":
        raise ValueError("predictive authority drift")

    for key in [
        "creates_signal",
        "operational_betting_authority",
        "probability_mutation_authorized",
        "eligibility_mutation_authorized",
        "value_or_ev_authorized",
        "stake_changes_authorized",
        "r1_r2_r3_changes_authorized",
        "production_integration_authorized",
        "ui_integration_authorized",
    ]:
        if guards.get(key) is not False:
            raise ValueError(f"authority guard drift: {key}")


def output_paths(ops: Path, config: dict[str, Any]) -> tuple[Path, Path, Path]:
    outputs = config.get("outputs") or {}
    values = [
        outputs.get("prematch_journal"),
        outputs.get("settlement_journal"),
        outputs.get("performance_report"),
    ]
    if any(not str(x or "").strip() for x in values):
        raise ValueError("missing output path")

    paths = []
    for value in values:
        p = Path(str(value))
        if p.is_absolute() or len(p.parts) != 1 or ".." in p.parts:
            raise ValueError("unsafe output path")
        paths.append(ops / p.name)
    return tuple(paths)


def canonical_fixture_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        fixture_id = str(row.get("api_fixture_id") or "").strip()
        if not fixture_id:
            continue
        cur = out.get(fixture_id)
        if cur is None:
            out[fixture_id] = row
            continue
        old_time = str(cur.get("weather_captured_at_utc") or "")
        new_time = str(row.get("weather_captured_at_utc") or "")
        if new_time and (not old_time or new_time < old_time):
            out[fixture_id] = row
    return out


def factor_presence(row: dict[str, str]) -> dict[str, str]:
    return {
        group: str(row.get(field) or "UNKNOWN").strip() or "UNKNOWN"
        for group, field in FACTOR_GROUP_FIELDS.items()
    }


def capture_prematch(
    feature_rows: list[dict[str, str]],
    existing: list[dict[str, Any]],
    observed_at: datetime,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    existing_fixture_ids = {str(e.get("fixture_id") or "") for e in existing}
    added = []
    diag = Counter()

    for fixture_id, row in canonical_fixture_rows(feature_rows).items():
        if fixture_id in existing_fixture_ids:
            diag["already_frozen"] += 1
            continue

        kickoff = parse_iso(row.get("kickoff_utc"))
        captured = parse_iso(row.get("weather_captured_at_utc"))

        if not kickoff:
            diag["invalid_kickoff"] += 1
            continue
        if observed_at >= kickoff:
            diag["skipped_after_kickoff_no_backfill"] += 1
            continue
        if str(row.get("weather_feature_status") or "") != "PREMATCH_FROZEN":
            diag["weather_not_frozen"] += 1
            continue
        if str(row.get("weather_evidence_time_status") or "") != "PREMATCH_FROZEN":
            diag["weather_time_not_frozen"] += 1
            continue
        if str(row.get("weather_usable_for_prematch") or "").lower() != "true":
            diag["weather_not_usable"] += 1
            continue
        if not captured or captured >= kickoff:
            diag["invalid_capture_time"] += 1
            continue
        if str(row.get("environment_feature_state") or "") == "DATA_MISSING_WEATHER":
            diag["data_missing_weather"] += 1
            continue
        if str(row.get("research_only") or "") != "YES":
            diag["research_contract_invalid"] += 1
            continue
        if str(row.get("predictive_authority") or "") != "NOT_AUTHORIZED":
            diag["authority_invalid"] += 1
            continue

        payload = {
            "fixture_id": fixture_id,
            "kickoff_utc": row.get("kickoff_utc") or "",
            "home_team": row.get("home_team") or "",
            "away_team": row.get("away_team") or "",
            "weather_snapshot_type": row.get("weather_snapshot_type") or "",
            "weather_captured_at_utc": row.get("weather_captured_at_utc") or "",
            "venue_id": row.get("venue_id") or "",
            "venue_name": row.get("venue_name") or "",
            "surface_provider": row.get("surface_provider") or "",
            "roof_type": row.get("roof_type") or "UNKNOWN",
            "roof_state_actual": row.get("roof_state_actual") or "UNKNOWN",
            "weather_exposure_resolution": row.get("weather_exposure_resolution") or "UNKNOWN",
            "environment_feature_state": row.get("environment_feature_state") or "",
            "factor_group_status": factor_presence(row),
            "features": {
                "temperature_c": row.get("temperature_c") or "",
                "apparent_temperature_c": row.get("apparent_temperature_c") or "",
                "relative_humidity_pct": row.get("relative_humidity_pct") or "",
                "dew_point_c": row.get("dew_point_c") or "",
                "apparent_temperature_delta_c": row.get("apparent_temperature_delta_c") or "",
                "wind_speed_10m_kmh": row.get("wind_speed_10m_kmh") or "",
                "wind_gusts_10m_kmh": row.get("wind_gusts_10m_kmh") or "",
                "wind_gust_spread_kmh": row.get("wind_gust_spread_kmh") or "",
                "precipitation_probability_pct": row.get("precipitation_probability_pct") or "",
                "precipitation_mm": row.get("precipitation_mm") or "",
                "rain_mm": row.get("rain_mm") or "",
                "showers_mm": row.get("showers_mm") or "",
                "snowfall_cm": row.get("snowfall_cm") or "",
                "visibility_m": row.get("visibility_m") or "",
                "weather_code": row.get("weather_code") or "",
                "thunderstorm_evidence": row.get("thunderstorm_evidence") or "",
                "dust_ug_m3": row.get("dust_ug_m3") or "",
                "pm10_ug_m3": row.get("pm10_ug_m3") or "",
                "pm2_5_ug_m3": row.get("pm2_5_ug_m3") or "",
                "aerosol_optical_depth": row.get("aerosol_optical_depth") or "",
                "european_aqi": row.get("european_aqi") or "",
                "elevation_m": row.get("elevation_m") or "",
                "altitude_zone": row.get("altitude_zone") or "",
            },
            "aggregate_environment_score": None,
            "double_counting_guard": True,
            "research_only": True,
            "predictive_authority": "NOT_AUTHORIZED",
            "betting_authority": "NOT_AUTHORIZED",
        }

        added.append({
            "event_id": event_id("PREMATCH", fixture_id),
            "event_type": "ENVIRONMENTAL_STRESS_V1_PREMATCH_FROZEN",
            "fixture_id": fixture_id,
            "frozen_at_utc": iso(observed_at),
            "payload": payload,
        })

    diag["prematch_events_created"] = len(added)
    return added, dict(diag)


def result_from_score(home: Any, away: Any) -> str | None:
    try:
        h = int(str(home).strip())
        a = int(str(away).strip())
    except (TypeError, ValueError):
        return None
    if h > a:
        return "H"
    if h < a:
        return "A"
    return "D"


def settle(
    overlay: list[dict[str, str]],
    prematch: list[dict[str, Any]],
    existing: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    frozen = {str(e.get("fixture_id") or ""): e for e in prematch}
    already = {str(e.get("fixture_id") or "") for e in existing}
    added = []
    diag = Counter()

    for row in overlay:
        fixture_id = str(row.get("fixture_id") or "").strip()
        if fixture_id not in frozen:
            continue
        if fixture_id in already:
            diag["already_settled"] += 1
            continue
        if str(row.get("status") or "").strip().lower() != "finished":
            diag["not_finished"] += 1
            continue
        if str(row.get("source_status") or "").strip().upper() != "FT":
            diag["not_exact_ft"] += 1
            continue

        result = result_from_score(row.get("score_home"), row.get("score_away"))
        settled_at = parse_iso(row.get("observed_at_utc"))
        kickoff = parse_iso(frozen[fixture_id].get("payload", {}).get("kickoff_utc"))

        if result is None or not settled_at or not kickoff or settled_at <= kickoff:
            diag["invalid_settlement"] += 1
            continue

        added.append({
            "event_id": event_id("SETTLEMENT", fixture_id),
            "event_type": "ENVIRONMENTAL_STRESS_V1_SETTLEMENT_FROZEN",
            "fixture_id": fixture_id,
            "frozen_at_utc": iso(settled_at),
            "payload": {
                "fixture_id": fixture_id,
                "kickoff_utc": frozen[fixture_id]["payload"]["kickoff_utc"],
                "result": result,
                "score_home": str(row.get("score_home") or ""),
                "score_away": str(row.get("score_away") or ""),
                "settled_at_utc": iso(settled_at),
                "prematch_event_id": frozen[fixture_id]["event_id"],
                "source": "STAGE71_EXISTING_OVERLAY_FT",
            },
        })

    diag["settlements_created"] = len(added)
    return added, dict(diag)


def performance_report(
    config: dict[str, Any],
    prematch: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
) -> dict[str, Any]:
    settled_by_fixture = {str(e.get("fixture_id") or ""): e for e in settlements}
    outcome_counts = Counter()
    group_known_counts = Counter()

    for event in prematch:
        fixture_id = str(event.get("fixture_id") or "")
        payload = event.get("payload") or {}
        groups = payload.get("factor_group_status") or {}

        for group in FACTOR_GROUP_FIELDS:
            status = str(groups.get(group) or "UNKNOWN")
            if status not in {"UNKNOWN", "", "OUTSIDE_FORECAST_HORIZON", "UNAVAILABLE"}:
                group_known_counts[group] += 1

        settled = settled_by_fixture.get(fixture_id)
        if settled:
            outcome_counts[str((settled.get("payload") or {}).get("result") or "UNKNOWN")] += 1

    review = config.get("forward_review") or {}
    minimum = int(review.get("minimum_settled_fixtures_for_formal_research", 500))
    min_class = int(review.get("minimum_outcomes_per_class", 50))
    settled_count = len(settlements)
    class_gate = all(outcome_counts.get(k, 0) >= min_class for k in ("H", "D", "A"))
    sample_gate = settled_count >= minimum and class_gate

    return {
        "version": VERSION,
        "research_id": EXPECTED_RESEARCH_ID,
        "status": "FORMAL_RESEARCH_SAMPLE_READY" if sample_gate else "FORWARD_EVIDENCE_ACCUMULATION",
        "prematch_frozen_fixtures": len(prematch),
        "settled_fixtures": settled_count,
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "factor_group_known_counts": {
            group: group_known_counts.get(group, 0)
            for group in FACTOR_GROUP_FIELDS
        },
        "minimum_settled_fixtures_for_formal_research": minimum,
        "minimum_outcomes_per_class": min_class,
        "formal_research_sample_ready": sample_gate,
        "automatic_factor_promotion": False,
        "automatic_model_promotion": False,
        "predictive_authority": "NOT_AUTHORIZED",
        "operational_betting_authority": False,
        "creates_signal": False,
        "historical_backfill": False,
        "aggregate_environment_score": False,
        "research_note": "Sample readiness only. No causal/predictive effect claim is made by this report.",
    }


def run(
    observed_at: datetime | None = None,
    ops: Path = OPS,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    observed_at = observed_at or now_utc()
    config = read_json(config_path)
    validate_contract(config)

    inputs = config["prospective_inputs"]
    if ops == OPS:
        feature_path = ROOT / inputs["feature_snapshot"]
        overlay_path = ROOT / inputs["settlement_overlay"]
    else:
        feature_path = ops / Path(inputs["feature_snapshot"]).name
        overlay_path = ops / Path(inputs["settlement_overlay"]).name

    prematch_path, settlement_path, report_path = output_paths(ops, config)

    prematch_raw, prematch = read_jsonl(prematch_path)
    settlement_raw, settlements = read_jsonl(settlement_path)

    new_prematch, capture_diag = capture_prematch(
        read_csv(feature_path),
        prematch,
        observed_at,
    )
    atomic_append(prematch_path, prematch_raw, new_prematch)
    prematch = prematch + new_prematch

    new_settlements, settlement_diag = settle(
        read_csv(overlay_path),
        prematch,
        settlements,
    )
    atomic_append(settlement_path, settlement_raw, new_settlements)
    settlements = settlements + new_settlements

    report = performance_report(config, prematch, settlements)
    atomic_json(report_path, report)

    result = {
        "run_at_utc": iso(observed_at),
        "status": "OK",
        "mode": "PROSPECTIVE_ONLY",
        "provider_calls_added": 0,
        "web_calls_added": 0,
        "historical_backfill": "FORBIDDEN",
        "capture": capture_diag,
        "settlement": settlement_diag,
        "prematch_frozen_fixtures": len(prematch),
        "settled_fixtures": len(settlements),
        "performance_status": report["status"],
        "formal_research_sample_ready": report["formal_research_sample_ready"],
        "predictive_authority": "NOT_AUTHORIZED",
        "operational_betting_authority": False,
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
