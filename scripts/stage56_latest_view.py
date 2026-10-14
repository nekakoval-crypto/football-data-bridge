#!/usr/bin/env python3
"""Rebuild Stage 56 compact latest view without collapsing numeric zero to blank."""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from pbk_data_registry import resolve

OPS = Path(os.getenv("OPS_DIR", "ops"))
# PBK488_PBK16_LATEST
FORWARD = resolve(
    "PBK.CAPTURE_UNIVERSE.PBK16.V1",
    require_class="DERIVED",
    require_scope="CURRENT",
    require_prematch=True,
)[0]
CONTEXT = OPS / "context_latest.csv"
WEATHER = OPS / "weather_snapshots.csv"
ROTATION = OPS / "rotation_snapshots.csv"
LATEST = OPS / "stage56_latest.csv"

ENVIRONMENT_MAX_FORECAST_GAP_MINUTES = 90.0

FIELDS = [
    "forward_id","rule","api_fixture_id","home_team","away_team",
    "kickoff_utc","weather_snapshot_type","weather_captured_at_utc",
    "weather_evidence_time_status","weather_usable_for_prematch",

    "elevation_m","altitude_zone",
    "temperature_c","apparent_temperature_c",
    "relative_humidity_pct","dew_point_c",
    "surface_pressure_hpa","cloud_cover_pct",

    "precipitation_probability_pct","precipitation_mm",
    "rain_mm","showers_mm","snowfall_cm",
    "weather_code","thunderstorm_evidence","visibility_m",

    "wind_speed_10m_kmh","wind_gusts_10m_kmh",
    "wind_direction_10m_deg",

    "air_quality_status","dust_ug_m3","pm10_ug_m3",
    "pm2_5_ug_m3","aerosol_optical_depth","european_aqi",

    "rotation_captured_at_utc",
    "home_retained_starters","away_retained_starters",
    "home_changed_starters","away_changed_starters",
    "home_retained_pct","away_retained_pct",
    "rotation_verified","context_only"
]


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    import csv
    import os
    import tempfile
    from pathlib import Path

    path = Path(path)
    fields = list(fields)
    rows = list(rows)

    def equivalent():
        if not path.is_file():
            return False

        try:
            with path.open(
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as stream:
                reader = csv.DictReader(stream)

                if list(reader.fieldnames or []) != fields:
                    return False

                sentinel = object()
                expected = iter(rows)

                for existing in reader:
                    candidate = next(expected, sentinel)

                    if candidate is sentinel:
                        return False

                    projected = {
                        field: str(
                            candidate.get(field, "")
                            if candidate.get(field, "") is not None
                            else ""
                        )
                        for field in fields
                    }

                    if existing != projected:
                        return False

                return next(expected, sentinel) is sentinel

        except (OSError, UnicodeError, csv.Error):
            return False

    if equivalent():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=path.parent,
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temp_name = stream.name

            writer = csv.DictWriter(
                stream,
                fieldnames=fields,
                extrasaction="ignore",
            )

            writer.writeheader()
            writer.writerows(rows)

            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temp_name, path)
        return True

    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def latest_by(rows, key="forward_id"):
    out = {}
    for r in rows:
        k = r.get(key) or ""
        if not k:
            continue
        cur = out.get(k)
        if cur is None or (r.get("captured_at_utc") or "") > (cur.get("captured_at_utc") or ""):
            out[k] = r
    return out


def val(row, key):
    value = row.get(key)
    return "" if value is None else value


def parse_iso(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def evidence_time_contract(row):
    captured = parse_iso(row.get("captured_at_utc"))
    kickoff = parse_iso(row.get("kickoff_utc"))

    if not captured or not kickoff:
        return "UNKNOWN", "false"

    if captured < kickoff:
        return "PREMATCH_FROZEN", "true"

    return "POSTMATCH_FACTUAL", "false"


from pbk_weather_evidence_gate import valid_weather_evidence

def valid_weather_row(row, fixture=None, context=None):
    return valid_weather_evidence(row, fixture, context)



def main():
    source_rows = read_csv(FORWARD)
    active = [
        r for r in source_rows
        if str(r.get("status") or "").strip() == "CAPTURE"
    ]

    if not active:
        raise SystemExit(
            "PBK488 FAIL-CLOSED: PBK16 capture universe empty"
        )

    ids = [
        str(r.get("forward_id") or "").strip()
        for r in active
    ]

    fixture_ids = [
        str(r.get("api_fixture_id") or "").strip()
        for r in active
    ]

    if any(not value for value in ids + fixture_ids):
        raise SystemExit(
            "PBK488 FAIL-CLOSED: missing capture identity"
        )

    if len(set(ids)) != len(ids):
        raise SystemExit(
            "PBK488 FAIL-CLOSED: duplicate forward IDs"
        )

    if len(set(fixture_ids)) != len(fixture_ids):
        raise SystemExit(
            "PBK488 FAIL-CLOSED: duplicate fixture IDs"
        )

    if any(
        forward != f"CAPTURE|{fixture}"
        for forward, fixture in zip(ids, fixture_ids)
    ):
        raise SystemExit(
            "PBK488 FAIL-CLOSED: inconsistent capture identities"
        )

    ctx = latest_by(read_csv(CONTEXT))
    # PBK542_SHARED_GEO_GATE
    active_by_id = {r['forward_id']: r for r in active}
    weather = latest_by([
        row
        for row in read_csv(WEATHER)
        if valid_weather_row(
            row,
            active_by_id.get(row.get('forward_id')),
            ctx.get(row.get('forward_id')),
        )
    ])
    rotation = latest_by(read_csv(ROTATION))

    rows = []
    for bet in active:
        fid = bet.get("forward_id") or ""
        c, w, r = ctx.get(fid, {}), weather.get(fid, {}), rotation.get(fid, {})
        time_status, usable = evidence_time_contract(w) if w else ("", "")
        rows.append({
            "forward_id": fid,
            "rule": val(bet, "rule"),
            "api_fixture_id": val(bet, "api_fixture_id"),
            "home_team": val(c, "home_team") or val(bet, "home_team"),
            "away_team": val(c, "away_team") or val(bet, "away_team"),
            "kickoff_utc": val(c, "current_kickoff_utc") or val(w, "kickoff_utc"),
            "weather_snapshot_type": val(w, "snapshot_type"),
            "weather_captured_at_utc": val(w, "captured_at_utc"),
            "weather_evidence_time_status": time_status,
            "weather_usable_for_prematch": usable,

            "elevation_m": val(w, "elevation_m"),
            "altitude_zone": val(w, "altitude_zone"),

            "temperature_c": val(w, "temperature_c"),
            "apparent_temperature_c": val(w, "apparent_temperature_c"),
            "relative_humidity_pct": val(w, "relative_humidity_pct"),
            "dew_point_c": val(w, "dew_point_c"),
            "surface_pressure_hpa": val(w, "surface_pressure_hpa"),
            "cloud_cover_pct": val(w, "cloud_cover_pct"),

            "precipitation_probability_pct": val(w, "precipitation_probability_pct"),
            "precipitation_mm": val(w, "precipitation_mm"),
            "rain_mm": val(w, "rain_mm"),
            "showers_mm": val(w, "showers_mm"),
            "snowfall_cm": val(w, "snowfall_cm"),

            "weather_code": val(w, "weather_code"),
            "thunderstorm_evidence": val(w, "thunderstorm_evidence"),
            "visibility_m": val(w, "visibility_m"),

            "wind_speed_10m_kmh": val(w, "wind_speed_10m_kmh"),
            "wind_gusts_10m_kmh": val(w, "wind_gusts_10m_kmh"),
            "wind_direction_10m_deg": val(w, "wind_direction_10m_deg"),

            "air_quality_status": val(w, "air_quality_status"),
            "dust_ug_m3": val(w, "dust_ug_m3"),
            "pm10_ug_m3": val(w, "pm10_ug_m3"),
            "pm2_5_ug_m3": val(w, "pm2_5_ug_m3"),
            "aerosol_optical_depth": val(w, "aerosol_optical_depth"),
            "european_aqi": val(w, "european_aqi"),
            "rotation_captured_at_utc": val(r, "captured_at_utc"),
            "home_retained_starters": val(r, "home_retained_starters"),
            "away_retained_starters": val(r, "away_retained_starters"),
            "home_changed_starters": val(r, "home_changed_starters"),
            "away_changed_starters": val(r, "away_changed_starters"),
            "home_retained_pct": val(r, "home_retained_pct"),
            "away_retained_pct": val(r, "away_retained_pct"),
            "rotation_verified": "YES" if r.get("home_rotation_verified") == "YES" and r.get("away_rotation_verified") == "YES" else "NO",
            "context_only": "YES",
        })
    if len(rows) != len(active):
        raise SystemExit(
            "PBK488 FAIL-CLOSED: incomplete latest view"
        )

    output_ids = [
        str(r.get("forward_id") or "").strip()
        for r in rows
    ]

    if set(output_ids) != set(ids):
        raise SystemExit(
            "PBK488 FAIL-CLOSED: latest identity mismatch"
        )

    write_csv(LATEST, FIELDS, rows)
    print(f"PBK488 CAPTURE ROWS = {len(active)}")
    print(f"PBK488 LATEST ROWS = {len(rows)}")
    print(f"PBK488 UNIQUE FIXTURES = {len(set(fixture_ids))}")
    print(f"PBK488 CONTRACT = PASS")
    print(f"stage56_latest_rows={len(rows)}")


if __name__ == "__main__":
    main()
