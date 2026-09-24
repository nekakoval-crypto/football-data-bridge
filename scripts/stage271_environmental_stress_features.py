#!/usr/bin/env python3
"""PBK #271 — Environmental Stress Features V1.

Research-only feature projection over PREMATCH_FROZEN weather plus canonical
venue/surface/roof context.

Principles:
- no provider/web calls;
- no post-kickoff weather;
- no numeric aggregate environment score;
- no predictive/betting/value/stake authority;
- no double counting: raw correlated observations stay inside named groups;
- missing weather remains DATA_MISSING_WEATHER, never numeric zero.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))

WEATHER = OPS / "stage56_latest.csv"
VENUE_STATE = OPS / "prematch_venue_state.csv"
VENUE_REGISTRY = OPS / "pbk16_venue_registry.csv"

OUTPUT = OPS / "environmental_stress_features.csv"
META = OPS / "stage271_environmental_stress_last_run.json"

VERSION = "PBK_ENVIRONMENTAL_STRESS_FEATURES_V1"

FIELDS = [
    "forward_id","rule","api_fixture_id","kickoff_utc",
    "home_team","away_team",

    "weather_feature_status",
    "weather_snapshot_type","weather_captured_at_utc",
    "weather_evidence_time_status","weather_usable_for_prematch",

    "venue_id","venue_name","surface_provider",
    "roof_type","roof_state_actual","roof_state_capture_status",
    "weather_exposure_resolution",
    "venue_environment_status",

    "temperature_c","apparent_temperature_c",
    "relative_humidity_pct","dew_point_c",
    "thermal_group_status","apparent_temperature_delta_c",
    "heat_humidity_joint_status",

    "wind_speed_10m_kmh","wind_gusts_10m_kmh",
    "wind_gust_spread_kmh","wind_group_status",

    "precipitation_probability_pct","precipitation_mm",
    "rain_mm","showers_mm","snowfall_cm",
    "precipitation_group_status",

    "visibility_m","weather_code","thunderstorm_evidence",
    "visibility_thunder_group_status",

    "air_quality_status","dust_ug_m3","pm10_ug_m3",
    "pm2_5_ug_m3","aerosol_optical_depth","european_aqi",
    "air_quality_group_status",

    "elevation_m","altitude_zone","altitude_group_status",
    "surface_group_status",

    "known_factor_groups","unknown_factor_groups",
    "environment_feature_state",

    "double_counting_policy",
    "context_only","research_only",
    "predictive_authority","betting_authority",
    "eligibility_mutation","probability_mutation","stake_changes",
    "projection_version",
]


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def fnum(value):
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def fmt(value):
    if value is None:
        return ""
    return f"{value:.3f}".rstrip("0").rstrip(".")


def by_key(rows, key):
    out = {}
    for row in rows:
        k = sval(row, key)
        if k:
            out[k] = row
    return out


def surface_by_venue(rows):
    out = {}
    for row in rows:
        venue_id = sval(row, "venue_id")
        if venue_id:
            out[venue_id] = sval(row, "surface_provider")
    return out


def group_known(*values):
    return any(v is not None and str(v).strip() != "" for v in values)


def build_feature_row(weather, venue, surface):
    fid = sval(weather, "forward_id") or sval(venue, "forward_id")
    prematch_weather = (
        sval(weather, "weather_usable_for_prematch").lower() == "true"
        and sval(weather, "weather_evidence_time_status") == "PREMATCH_FROZEN"
    )

    temp = fnum(weather.get("temperature_c"))
    apparent = fnum(weather.get("apparent_temperature_c"))
    humidity = fnum(weather.get("relative_humidity_pct"))
    dew = fnum(weather.get("dew_point_c"))

    wind = fnum(weather.get("wind_speed_10m_kmh"))
    gust = fnum(weather.get("wind_gusts_10m_kmh"))

    precip_prob = fnum(weather.get("precipitation_probability_pct"))
    precip = fnum(weather.get("precipitation_mm"))
    rain = fnum(weather.get("rain_mm"))
    showers = fnum(weather.get("showers_mm"))
    snowfall = fnum(weather.get("snowfall_cm"))

    visibility = fnum(weather.get("visibility_m"))
    weather_code = sval(weather, "weather_code")
    thunder = sval(weather, "thunderstorm_evidence")

    dust = fnum(weather.get("dust_ug_m3"))
    pm10 = fnum(weather.get("pm10_ug_m3"))
    pm25 = fnum(weather.get("pm2_5_ug_m3"))
    aod = fnum(weather.get("aerosol_optical_depth"))
    aqi = fnum(weather.get("european_aqi"))

    elevation = fnum(weather.get("elevation_m"))
    altitude_zone = sval(weather, "altitude_zone")

    if not prematch_weather:
        thermal_status = wind_status = precip_status = "UNKNOWN"
        visibility_status = air_status = altitude_status = "UNKNOWN"
        feature_state = "DATA_MISSING_WEATHER"
        heat_humidity = "UNKNOWN"
    else:
        thermal_status = "KNOWN" if group_known(temp, apparent, humidity, dew) else "UNKNOWN"
        wind_status = "KNOWN" if group_known(wind, gust) else "UNKNOWN"
        precip_status = "KNOWN" if group_known(precip_prob, precip, rain, showers, snowfall) else "UNKNOWN"
        visibility_status = "KNOWN" if group_known(visibility, weather_code, thunder) else "UNKNOWN"
        air_status = (
            "KNOWN"
            if sval(weather, "air_quality_status") == "CAPTURED"
            and group_known(dust, pm10, pm25, aod, aqi)
            else sval(weather, "air_quality_status") or "UNKNOWN"
        )
        altitude_status = "KNOWN" if elevation is not None or altitude_zone not in {"", "UNKNOWN"} else "UNKNOWN"
        heat_humidity = "KNOWN_PAIR" if temp is not None and humidity is not None else "UNKNOWN"
        feature_state = "RESEARCH_FEATURES_AVAILABLE"

    roof_resolution = sval(venue, "weather_exposure_resolution") or "UNKNOWN"
    roof_capture = sval(venue, "roof_state_capture_status") or "UNKNOWN"

    if roof_resolution == "UNRESOLVED_RETRACTABLE_ROOF_STATE":
        venue_environment_status = "UNRESOLVED_RETRACTABLE_ROOF_STATE"
        if feature_state == "RESEARCH_FEATURES_AVAILABLE":
            feature_state = "RESEARCH_FEATURES_WITH_UNRESOLVED_VENUE_STATE"
    elif roof_resolution == "ROOF_CLOSED_WEATHER_SHIELDED":
        venue_environment_status = "ROOF_CLOSED"
    elif roof_resolution in {
        "ROOF_OPEN_OR_PARTIAL_WEATHER_EXPOSED",
        "OPEN_PITCH_WEATHER_EXPOSED",
    }:
        venue_environment_status = "WEATHER_EXPOSED"
    else:
        venue_environment_status = roof_resolution or "UNKNOWN"

    surface_status = "KNOWN" if surface else "UNKNOWN"

    statuses = {
        "THERMAL": thermal_status,
        "WIND_GUST": wind_status,
        "PRECIPITATION": precip_status,
        "VISIBILITY_THUNDER": visibility_status,
        "AIR_QUALITY": air_status,
        "ALTITUDE": altitude_status,
        "SURFACE": surface_status,
        "ROOF_EXPOSURE": "KNOWN" if venue_environment_status not in {"", "UNKNOWN"} else "UNKNOWN",
    }

    known = sum(v == "KNOWN" or v in {"KNOWN_PAIR", "CAPTURED", "ROOF_CLOSED", "WEATHER_EXPOSED"} for v in statuses.values())
    unknown = len(statuses) - known

    return {
        "forward_id": fid,
        "rule": sval(weather, "rule") or sval(venue, "rule"),
        "api_fixture_id": sval(weather, "api_fixture_id") or sval(venue, "api_fixture_id"),
        "kickoff_utc": sval(weather, "kickoff_utc") or sval(venue, "kickoff_utc"),
        "home_team": sval(weather, "home_team") or sval(venue, "home_team"),
        "away_team": sval(weather, "away_team") or sval(venue, "away_team"),

        "weather_feature_status": "PREMATCH_FROZEN" if prematch_weather else "MISSING",
        "weather_snapshot_type": sval(weather, "weather_snapshot_type"),
        "weather_captured_at_utc": sval(weather, "weather_captured_at_utc"),
        "weather_evidence_time_status": sval(weather, "weather_evidence_time_status"),
        "weather_usable_for_prematch": sval(weather, "weather_usable_for_prematch"),

        "venue_id": sval(venue, "venue_id"),
        "venue_name": sval(venue, "venue_name"),
        "surface_provider": surface,
        "roof_type": sval(venue, "roof_type") or "UNKNOWN",
        "roof_state_actual": sval(venue, "roof_state_actual") or "UNKNOWN",
        "roof_state_capture_status": roof_capture,
        "weather_exposure_resolution": roof_resolution,
        "venue_environment_status": venue_environment_status,

        "temperature_c": sval(weather, "temperature_c"),
        "apparent_temperature_c": sval(weather, "apparent_temperature_c"),
        "relative_humidity_pct": sval(weather, "relative_humidity_pct"),
        "dew_point_c": sval(weather, "dew_point_c"),
        "thermal_group_status": thermal_status,
        "apparent_temperature_delta_c": fmt(apparent - temp) if apparent is not None and temp is not None else "",
        "heat_humidity_joint_status": heat_humidity,

        "wind_speed_10m_kmh": sval(weather, "wind_speed_10m_kmh"),
        "wind_gusts_10m_kmh": sval(weather, "wind_gusts_10m_kmh"),
        "wind_gust_spread_kmh": fmt(gust - wind) if gust is not None and wind is not None else "",
        "wind_group_status": wind_status,

        "precipitation_probability_pct": sval(weather, "precipitation_probability_pct"),
        "precipitation_mm": sval(weather, "precipitation_mm"),
        "rain_mm": sval(weather, "rain_mm"),
        "showers_mm": sval(weather, "showers_mm"),
        "snowfall_cm": sval(weather, "snowfall_cm"),
        "precipitation_group_status": precip_status,

        "visibility_m": sval(weather, "visibility_m"),
        "weather_code": weather_code,
        "thunderstorm_evidence": thunder,
        "visibility_thunder_group_status": visibility_status,

        "air_quality_status": sval(weather, "air_quality_status"),
        "dust_ug_m3": sval(weather, "dust_ug_m3"),
        "pm10_ug_m3": sval(weather, "pm10_ug_m3"),
        "pm2_5_ug_m3": sval(weather, "pm2_5_ug_m3"),
        "aerosol_optical_depth": sval(weather, "aerosol_optical_depth"),
        "european_aqi": sval(weather, "european_aqi"),
        "air_quality_group_status": air_status,

        "elevation_m": sval(weather, "elevation_m"),
        "altitude_zone": altitude_zone,
        "altitude_group_status": altitude_status,
        "surface_group_status": surface_status,

        "known_factor_groups": str(known),
        "unknown_factor_groups": str(unknown),
        "environment_feature_state": feature_state,

        "double_counting_policy": (
            "NO_AGGREGATE_SCORE; thermal raw values stay one group; "
            "wind+gust one group; precipitation components one group; "
            "AQ pollutants one group; downstream models must select within groups"
        ),
        "context_only": "YES",
        "research_only": "YES",
        "predictive_authority": "NOT_AUTHORIZED",
        "betting_authority": "NOT_AUTHORIZED",
        "eligibility_mutation": "false",
        "probability_mutation": "false",
        "stake_changes": "false",
        "projection_version": VERSION,
    }


def build_rows(weather_rows, venue_rows, registry_rows):
    weather = by_key(weather_rows, "forward_id")
    venues = by_key(venue_rows, "forward_id")
    surfaces = surface_by_venue(registry_rows)

    keys = sorted(set(weather) | set(venues))
    rows = []
    for fid in keys:
        w = weather.get(fid, {})
        v = venues.get(fid, {})
        surface = surfaces.get(sval(v, "venue_id"), "")
        rows.append(build_feature_row(w, v, surface))
    return rows


def main():
    rows = build_rows(
        read_csv(WEATHER),
        read_csv(VENUE_STATE),
        read_csv(VENUE_REGISTRY),
    )
    write_csv(OUTPUT, rows)

    states = Counter(r["environment_feature_state"] for r in rows)
    meta = {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "OK",
        "rows": len(rows),
        "state_counts": dict(sorted(states.items())),
        "provider_calls": 0,
        "web_calls": 0,
        "aggregate_environment_score": False,
        "double_counting_guard": True,
        "postmatch_weather_allowed": False,
        "research_only": True,
        "predictive_authority": "NOT_AUTHORIZED",
        "betting_authority": "NOT_AUTHORIZED",
        "next_stage": (
            "Historical/prospective research by named factor group and market; "
            "no automatic promotion from descriptive feature availability."
        ),
    }

    META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
