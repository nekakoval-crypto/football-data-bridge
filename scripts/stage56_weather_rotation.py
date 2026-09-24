#!/usr/bin/env python3
"""Stage 56: weather + official-XI rotation context for canonical PBK forward signals.

This layer is explanatory only. It never changes R1/R2/R3 eligibility, the
immutable Bet365 trigger, or the paper-forward stake.

Weather snapshots are append-only at BASELINE/T24/T3/T60. Venue city is
geocoded with Open-Meteo Geocoding and weather is taken from the nearest hourly
forecast point to kickoff.

XI/rotation is captured once official current lineups are published. Rotation
is measured against the official starting XI from each team's previous fixture
recorded by Stage 55. Missing previous lineups remain missing; no inference is
made.
"""
from __future__ import annotations

import csv
import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from api_football_broker import api_get as broker_api_get

OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
CONTEXT = OPS / "context_latest.csv"
WEATHER = OPS / "weather_snapshots.csv"
ROTATION = OPS / "rotation_snapshots.csv"
LATEST = OPS / "stage56_latest.csv"
META = OPS / "stage56_last_run.json"

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_AIR_QUALITY = "https://air-quality-api.open-meteo.com/v1/air-quality"

OPEN_METEO_FORECAST_DAYS = 16
OPEN_METEO_AIR_QUALITY_DAYS = 7

WEATHER_BASELINE_MAX_HOURS = (OPEN_METEO_FORECAST_DAYS - 1) * 24.0
AIR_QUALITY_MAX_HOURS = (OPEN_METEO_AIR_QUALITY_DAYS - 1) * 24.0

# Hard fail-closed maximum. A provider point farther away than this
# is not accepted as weather for the fixture.
ENVIRONMENT_MAX_FORECAST_GAP_MINUTES = 90.0

COUNTRY_CODE_BY_DIV = {
    "E0": "GB",
    "SP1": "ES",
    "I1": "IT",
    "D1": "DE",
    "F1": "FR",
}

COUNTRY_CODE_BY_LEAGUE = {
    "Premier League": "GB",
    "La Liga": "ES",
    "Serie A": "IT",
    "Bundesliga": "DE",
    "Ligue 1": "FR",
    "Austrian Bundesliga": "AT",
    "Bundesliga Austria": "AT",
    "Belgian Pro League": "BE",
    "Jupiler Pro League": "BE",
    "Danish Superliga": "DK",
    "Superliga": "DK",
    "A Lyga": "LT",
    "Virsliga": "LV",
    "Eredivisie": "NL",
    "Eliteserien": "NO",
    "Ekstraklasa": "PL",
    "Primeira Liga": "PT",
    "Super Lig": "TR",
    "Süper Lig": "TR",
    "Scottish Premiership": "GB",
}

WEATHER_FIELDS = [
    "forward_id","rule","api_fixture_id","snapshot_type",
    "captured_at_utc","kickoff_utc","hours_to_kickoff",
    "evidence_time_status","usable_for_prematch",
    "venue_name","venue_city","geocoded_name","country_code",
    "latitude","longitude",

    "elevation_m","altitude_zone","elevation_source",

    "forecast_time_utc","forecast_gap_minutes",
    "temperature_c","apparent_temperature_c",
    "relative_humidity_pct","dew_point_c",
    "surface_pressure_hpa","cloud_cover_pct",

    "precipitation_probability_pct","precipitation_mm",
    "rain_mm","showers_mm","snowfall_cm",

    "weather_code","thunderstorm_evidence",
    "visibility_m",

    "wind_speed_10m_kmh","wind_gusts_10m_kmh",
    "wind_direction_10m_deg",

    "air_quality_status","air_quality_time_utc",
    "air_quality_gap_minutes","dust_ug_m3",
    "pm10_ug_m3","pm2_5_ug_m3",
    "aerosol_optical_depth","european_aqi",

    "source","context_only","notes"
]

ROTATION_FIELDS = [
    "forward_id","rule","api_fixture_id","captured_at_utc","kickoff_utc","minutes_to_kickoff",
    "home_team","away_team","home_team_id","away_team_id","home_prev_fixture_id","away_prev_fixture_id",
    "home_prev_competition","away_prev_competition","home_prev_comp_class","away_prev_comp_class",
    "home_current_formation","away_current_formation","home_current_coach","away_current_coach",
    "home_current_xi_json","away_current_xi_json","home_prev_xi_json","away_prev_xi_json",
    "home_current_xi_count","away_current_xi_count","home_prev_xi_count","away_prev_xi_count",
    "home_retained_starters","away_retained_starters","home_changed_starters","away_changed_starters",
    "home_retained_pct","away_retained_pct","home_rotation_verified","away_rotation_verified",
    "current_lineups_available","previous_lineups_complete","context_only","notes"
]

LATEST_FIELDS = [
    "forward_id","rule","api_fixture_id","home_team","away_team","kickoff_utc",
    "weather_snapshot_type","weather_captured_at_utc","temperature_c","precipitation_probability_pct",
    "precipitation_mm","wind_speed_10m_kmh","wind_gusts_10m_kmh","visibility_m","weather_code",
    "rotation_captured_at_utc","home_retained_starters","away_retained_starters","home_changed_starters",
    "away_changed_starters","home_retained_pct","away_retained_pct","rotation_verified","context_only"
]


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def fnum(x):
    try:
        v = float(str(x).strip())
        return v if math.isfinite(v) else None
    except Exception:
        return None


def read_csv(path):
    if not path.exists():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def http_json(url, headers=None, attempts=3):
    last = None
    for n in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers=headers or {"User-Agent": "football-data-bridge/6.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as exc:
            last = exc
            if n < attempts:
                time.sleep(n * 3)
    raise last


def api_get(path, params=None, **kwargs):
    return broker_api_get(path, params, **kwargs)


def om_get(base, params):
    return http_json(base + "?" + urllib.parse.urlencode(params, doseq=True), {"User-Agent": "football-data-bridge/6.0"})


def weather_due_type(done, forward_id, hours):
    if (
        0.0 < hours <= WEATHER_BASELINE_MAX_HOURS
        and (forward_id, "BASELINE") not in done
    ):
        return "BASELINE"

    if 6.0 < hours <= 30.0 and (forward_id, "T24") not in done:
        return "T24"

    if 1.5 < hours <= 6.0 and (forward_id, "T3") not in done:
        return "T3"

    if 0.0 < hours <= 1.5 and (forward_id, "T60") not in done:
        return "T60"

    return ""


def country_code_for(bet, context):
    league = str((context or {}).get("league") or "").strip()
    if league in COUNTRY_CODE_BY_LEAGUE:
        return COUNTRY_CODE_BY_LEAGUE[league]

    return COUNTRY_CODE_BY_DIV.get(
        str((bet or {}).get("div") or "").strip(),
        "",
    )


def altitude_zone(value):
    elevation = fnum(value)

    if elevation is None:
        return "UNKNOWN"
    if elevation < 0:
        return "BELOW_SEA_LEVEL"
    if elevation < 500:
        return "ALTITUDE_NORMAL"
    if elevation < 1000:
        return "ALTITUDE_ELEVATED"
    if elevation < 1500:
        return "ALTITUDE_MATERIAL"
    if elevation < 2000:
        return "ALTITUDE_HIGH"
    return "ALTITUDE_VERY_HIGH"


def thunderstorm_evidence(value):
    try:
        code = int(float(value))
    except (TypeError, ValueError):
        return "UNKNOWN"

    return "YES" if code in {95, 96, 99} else "NO"


def evidence_time_contract(captured_at, kickoff_at):
    captured = captured_at if isinstance(captured_at, datetime) else parse_iso(captured_at)
    kickoff = kickoff_at if isinstance(kickoff_at, datetime) else parse_iso(kickoff_at)

    if not captured or not kickoff:
        return {
            "evidence_time_status": "UNKNOWN",
            "usable_for_prematch": "false",
        }

    if captured < kickoff:
        return {
            "evidence_time_status": "PREMATCH_FROZEN",
            "usable_for_prematch": "true",
        }

    return {
        "evidence_time_status": "POSTMATCH_FACTUAL",
        "usable_for_prematch": "false",
    }


def valid_prematch_weather_row(row):
    try:
        gap = float(str(row.get("forecast_gap_minutes") or "").strip())
    except (TypeError, ValueError):
        return False

    if not (0.0 <= gap <= ENVIRONMENT_MAX_FORECAST_GAP_MINUTES):
        return False

    contract = evidence_time_contract(
        row.get("captured_at_utc"),
        row.get("kickoff_utc"),
    )
    return contract["usable_for_prematch"] == "true"


def weather_done_keys(rows):
    return {
        (row.get("forward_id"), row.get("snapshot_type"))
        for row in rows
        if valid_prematch_weather_row(row)
    }


def geocode_city(city, country_code):
    if not city:
        return None
    d = om_get(OPEN_METEO_GEOCODING, {"name": city, "count": 10, "language": "en", "format": "json"})
    rows = d.get("results") or []
    if country_code:
        exact_country = [r for r in rows if str(r.get("country_code") or "").upper() == country_code]
        if exact_country:
            rows = exact_country
    if not rows:
        return None
    # Prefer exact normalized city name, otherwise the provider's first ranked result.
    exact = [r for r in rows if str(r.get("name") or "").strip().casefold() == city.strip().casefold()]
    return (exact or rows)[0]


def _nearest_hourly_row(hourly, kickoff, variables):
    times = hourly.get("time") or []

    parsed = [
        parse_iso(
            str(value) + ":00Z"
            if len(str(value)) == 16
            else str(value)
        )
        for value in times
    ]

    candidates = [
        (abs((dt - kickoff).total_seconds()), idx, dt)
        for idx, dt in enumerate(parsed)
        if dt
    ]

    if not candidates:
        return None

    _, idx, dt = min(candidates, key=lambda item: item[0])

    gap = abs((dt - kickoff).total_seconds()) / 60.0

    if gap > ENVIRONMENT_MAX_FORECAST_GAP_MINUTES:
        return None

    row = {
        "forecast_time": dt,
        "forecast_gap_minutes": gap,
    }

    for variable in variables:
        values = hourly.get(variable) or []
        row[variable] = values[idx] if idx < len(values) else None

    return row


def nearest_hourly_weather(lat, lon, kickoff):
    variables = [
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "dew_point_2m",
        "surface_pressure",
        "cloud_cover",
        "precipitation_probability",
        "precipitation",
        "rain",
        "showers",
        "snowfall",
        "weather_code",
        "visibility",
        "wind_speed_10m",
        "wind_gusts_10m",
        "wind_direction_10m",
    ]

    data = om_get(
        OPEN_METEO_FORECAST,
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(variables),
            "timezone": "UTC",
            "forecast_days": OPEN_METEO_FORECAST_DAYS,
        },
    )

    return _nearest_hourly_row(
        data.get("hourly") or {},
        kickoff,
        variables,
    )


def nearest_hourly_air_quality(lat, lon, kickoff):
    variables = [
        "dust",
        "pm10",
        "pm2_5",
        "aerosol_optical_depth",
        "european_aqi",
    ]

    data = om_get(
        OPEN_METEO_AIR_QUALITY,
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(variables),
            "timezone": "UTC",
            "forecast_days": OPEN_METEO_AIR_QUALITY_DAYS,
        },
    )

    return _nearest_hourly_row(
        data.get("hourly") or {},
        kickoff,
        variables,
    )


def get_lineups(fixture_id):
    d = api_get("/fixtures/lineups", {"fixture": fixture_id}, force_refresh=True)
    return d.get("response") or []


def team_lineup(lineups, team_id):
    tid = int(team_id or 0)
    for item in lineups:
        team = item.get("team") or {}
        if int(team.get("id") or 0) != tid:
            continue
        xi = []
        for z in item.get("startXI") or []:
            p = z.get("player") or {}
            xi.append({
                "id": p.get("id"), "name": p.get("name"), "number": p.get("number"),
                "pos": p.get("pos"), "grid": p.get("grid")
            })
        return {
            "formation": item.get("formation") or "",
            "coach": (item.get("coach") or {}).get("name") or "",
            "xi": xi,
        }
    return {"formation": "", "coach": "", "xi": []}


def xi_ids(xi):
    return {str(p.get("id")) for p in xi if p.get("id") not in (None, "")}


def rotation_metrics(current_xi, previous_xi):
    cur, prev = xi_ids(current_xi), xi_ids(previous_xi)
    if len(cur) != 11 or len(prev) != 11:
        return {"verified": "NO", "retained": "", "changed": "", "retained_pct": ""}
    retained = len(cur & prev)
    return {
        "verified": "YES",
        "retained": retained,
        "changed": 11 - retained,
        "retained_pct": f"{retained / 11.0 * 100:.1f}",
    }


def context_by_forward(rows):
    out = {}
    for r in rows:
        fid = r.get("forward_id") or ""
        if not fid:
            continue
        cur = out.get(fid)
        if cur is None or (r.get("captured_at_utc") or "") > (cur.get("captured_at_utc") or ""):
            out[fid] = r
    return out


def main():
    now = now_utc()
    forward, _ = read_csv(FORWARD)
    context_rows, _ = read_csv(CONTEXT)
    weather_rows, _ = read_csv(WEATHER)
    rotation_rows, _ = read_csv(ROTATION)
    ctx = context_by_forward(context_rows)

    active = [r for r in forward if r.get("status") in {"PAPER", "OPEN", "REVIEW"}]
    weather_done = weather_done_keys(weather_rows)
    rotation_done = {r.get("forward_id") for r in rotation_rows}

    new_weather = 0
    new_rotation = 0
    geocoding_calls = 0
    weather_calls = 0
    air_quality_calls = 0
    current_lineup_calls = 0
    previous_lineup_calls = 0
    warnings = []

    for bet in active:
        fid = bet.get("forward_id") or ""
        c = ctx.get(fid) or {}
        kickoff = parse_iso(c.get("current_kickoff_utc"))
        if not kickoff:
            # Fallback to Stage 53 date/time, which is stored in UTC by the screener.
            kickoff = parse_iso(f"{bet.get('match_date')}T{bet.get('kickoff_time')}:00Z")
        if not kickoff:
            warnings.append(f"{fid}: kickoff unavailable")
            continue
        hours = (kickoff - now).total_seconds() / 3600.0
        if hours <= 0:
            continue

        # ---------- Weather ----------
        stype = weather_due_type(weather_done, fid, hours)
        if stype:
            city = c.get("venue_city") or ""
            country_code = country_code_for(bet, c)
            try:
                geo = geocode_city(city, country_code)
                geocoding_calls += 1
                if not geo:
                    raise RuntimeError(f"no geocoding result for {city!r}/{country_code}")
                latitude = geo.get("latitude")
                longitude = geo.get("longitude")
                elevation = geo.get("elevation")

                w = nearest_hourly_weather(
                    latitude,
                    longitude,
                    kickoff,
                )
                weather_calls += 1

                if not w:
                    raise RuntimeError(
                        "no hourly weather forecast within "
                        "fail-closed kickoff gap"
                    )

                air = None
                air_status = "OUTSIDE_FORECAST_HORIZON"

                if 0.0 < hours <= AIR_QUALITY_MAX_HOURS:
                    try:
                        air = nearest_hourly_air_quality(
                            latitude,
                            longitude,
                            kickoff,
                        )
                        air_quality_calls += 1
                        air_status = "CAPTURED" if air else "UNAVAILABLE"
                    except Exception as exc:
                        air_status = "UNAVAILABLE"
                        warnings.append(f"air quality {fid}: {exc}")

                time_contract = evidence_time_contract(now, kickoff)

                if time_contract["usable_for_prematch"] != "true":
                    raise RuntimeError("weather snapshot is not prematch-safe")

                weather_rows.append({
                    "forward_id": fid,
                    "rule": bet.get("rule") or "",
                    "api_fixture_id": bet.get("api_fixture_id") or "",
                    "snapshot_type": stype,
                    "captured_at_utc": iso(now),
                    "kickoff_utc": iso(kickoff),
                    "hours_to_kickoff": f"{hours:.2f}",
                    "evidence_time_status": time_contract["evidence_time_status"],
                    "usable_for_prematch": time_contract["usable_for_prematch"],
                    "venue_name": c.get("venue_name") or "",
                    "venue_city": city,
                    "geocoded_name": geo.get("name") or "",
                    "country_code": geo.get("country_code") or country_code,
                    "latitude": geo.get("latitude") if geo.get("latitude") is not None else "",
                    "longitude": geo.get("longitude") if geo.get("longitude") is not None else "",
                    "elevation_m": (
                        elevation if elevation is not None else ""
                    ),
                    "altitude_zone": altitude_zone(elevation),
                    "elevation_source": (
                        "Open-Meteo city geocoding elevation proxy"
                    ),

                    "forecast_time_utc": iso(w.get("forecast_time")),
                    "forecast_gap_minutes": (
                        f"{w.get('forecast_gap_minutes'):.1f}"
                    ),

                    "temperature_c": w.get("temperature_2m") if w.get("temperature_2m") is not None else "",
                    "apparent_temperature_c": w.get("apparent_temperature") if w.get("apparent_temperature") is not None else "",
                    "relative_humidity_pct": w.get("relative_humidity_2m") if w.get("relative_humidity_2m") is not None else "",
                    "dew_point_c": w.get("dew_point_2m") if w.get("dew_point_2m") is not None else "",
                    "surface_pressure_hpa": w.get("surface_pressure") if w.get("surface_pressure") is not None else "",
                    "cloud_cover_pct": w.get("cloud_cover") if w.get("cloud_cover") is not None else "",

                    "precipitation_probability_pct": w.get("precipitation_probability") if w.get("precipitation_probability") is not None else "",
                    "precipitation_mm": w.get("precipitation") if w.get("precipitation") is not None else "",
                    "rain_mm": w.get("rain") if w.get("rain") is not None else "",
                    "showers_mm": w.get("showers") if w.get("showers") is not None else "",
                    "snowfall_cm": w.get("snowfall") if w.get("snowfall") is not None else "",

                    "weather_code": w.get("weather_code") if w.get("weather_code") is not None else "",
                    "thunderstorm_evidence": thunderstorm_evidence(
                        w.get("weather_code")
                    ),

                    "visibility_m": w.get("visibility") if w.get("visibility") is not None else "",

                    "wind_speed_10m_kmh": w.get("wind_speed_10m") if w.get("wind_speed_10m") is not None else "",
                    "wind_gusts_10m_kmh": w.get("wind_gusts_10m") if w.get("wind_gusts_10m") is not None else "",
                    "wind_direction_10m_deg": w.get("wind_direction_10m") if w.get("wind_direction_10m") is not None else "",

                    "air_quality_status": air_status,
                    "air_quality_time_utc": (
                        iso(air.get("forecast_time")) if air else ""
                    ),
                    "air_quality_gap_minutes": (
                        f"{air.get('forecast_gap_minutes'):.1f}"
                        if air else ""
                    ),
                    "dust_ug_m3": air.get("dust") if air and air.get("dust") is not None else "",
                    "pm10_ug_m3": air.get("pm10") if air and air.get("pm10") is not None else "",
                    "pm2_5_ug_m3": air.get("pm2_5") if air and air.get("pm2_5") is not None else "",
                    "aerosol_optical_depth": air.get("aerosol_optical_depth") if air and air.get("aerosol_optical_depth") is not None else "",
                    "european_aqi": air.get("european_aqi") if air and air.get("european_aqi") is not None else "",

                    "source": (
                        "Open-Meteo weather + Air Quality when available; "
                        "venue-city geocoding"
                    ),
                    "context_only": "YES",
                    "notes": (
                        "environment evidence only; no predictive, "
                        "eligibility, value or stake authority"
                    ),
                })
                weather_done.add((fid, stype))
                new_weather += 1
            except Exception as exc:
                warnings.append(f"weather {fid}: {exc}")

        # ---------- Official XI + rotation ----------
        # Poll only in the final 90 minutes and only until captured once.
        if 0 < hours <= 1.5 and fid not in rotation_done:
            fixture_id = bet.get("api_fixture_id") or ""
            try:
                current_lineups = get_lineups(fixture_id)
                current_lineup_calls += 1
            except Exception as exc:
                warnings.append(f"current lineup {fid}: {exc}")
                current_lineups = []
            if not current_lineups:
                continue

            home_id = c.get("home_team_id") or ""
            away_id = c.get("away_team_id") or ""
            cur_home = team_lineup(current_lineups, home_id)
            cur_away = team_lineup(current_lineups, away_id)
            if len(cur_home["xi"]) != 11 or len(cur_away["xi"]) != 11:
                # Do not freeze partial/placeholder lineups.
                continue

            prev_home = {"formation": "", "coach": "", "xi": []}
            prev_away = {"formation": "", "coach": "", "xi": []}
            hp_id = c.get("home_prev_fixture_id") or ""
            ap_id = c.get("away_prev_fixture_id") or ""
            if hp_id:
                try:
                    prev_home = team_lineup(get_lineups(hp_id), home_id)
                    previous_lineup_calls += 1
                except Exception as exc:
                    warnings.append(f"home previous lineup {fid}: {exc}")
            if ap_id:
                try:
                    prev_away = team_lineup(get_lineups(ap_id), away_id)
                    previous_lineup_calls += 1
                except Exception as exc:
                    warnings.append(f"away previous lineup {fid}: {exc}")

            hm = rotation_metrics(cur_home["xi"], prev_home["xi"])
            am = rotation_metrics(cur_away["xi"], prev_away["xi"])
            notes = []
            if hm["verified"] != "YES": notes.append("home previous official XI unavailable/incomplete")
            if am["verified"] != "YES": notes.append("away previous official XI unavailable/incomplete")

            rotation_rows.append({
                "forward_id": fid,
                "rule": bet.get("rule") or "",
                "api_fixture_id": fixture_id,
                "captured_at_utc": iso(now),
                "kickoff_utc": iso(kickoff),
                "minutes_to_kickoff": f"{hours * 60.0:.1f}",
                "home_team": c.get("home_team") or bet.get("home_team") or "",
                "away_team": c.get("away_team") or bet.get("away_team") or "",
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_prev_fixture_id": hp_id,
                "away_prev_fixture_id": ap_id,
                "home_prev_competition": c.get("home_prev_competition") or "",
                "away_prev_competition": c.get("away_prev_competition") or "",
                "home_prev_comp_class": c.get("home_prev_comp_class") or "",
                "away_prev_comp_class": c.get("away_prev_comp_class") or "",
                "home_current_formation": cur_home["formation"],
                "away_current_formation": cur_away["formation"],
                "home_current_coach": cur_home["coach"],
                "away_current_coach": cur_away["coach"],
                "home_current_xi_json": json.dumps(cur_home["xi"], ensure_ascii=False, separators=(",", ":")),
                "away_current_xi_json": json.dumps(cur_away["xi"], ensure_ascii=False, separators=(",", ":")),
                "home_prev_xi_json": json.dumps(prev_home["xi"], ensure_ascii=False, separators=(",", ":")),
                "away_prev_xi_json": json.dumps(prev_away["xi"], ensure_ascii=False, separators=(",", ":")),
                "home_current_xi_count": len(cur_home["xi"]),
                "away_current_xi_count": len(cur_away["xi"]),
                "home_prev_xi_count": len(prev_home["xi"]),
                "away_prev_xi_count": len(prev_away["xi"]),
                "home_retained_starters": hm["retained"],
                "away_retained_starters": am["retained"],
                "home_changed_starters": hm["changed"],
                "away_changed_starters": am["changed"],
                "home_retained_pct": hm["retained_pct"],
                "away_retained_pct": am["retained_pct"],
                "home_rotation_verified": hm["verified"],
                "away_rotation_verified": am["verified"],
                "current_lineups_available": "YES",
                "previous_lineups_complete": "YES" if hm["verified"] == "YES" and am["verified"] == "YES" else "NO",
                "context_only": "YES",
                "notes": "; ".join(notes),
            })
            rotation_done.add(fid)
            new_rotation += 1

    write_csv(WEATHER, WEATHER_FIELDS, weather_rows)
    write_csv(ROTATION, ROTATION_FIELDS, rotation_rows)

    # Compact latest view for daily consumption.
    weather_latest = {}
    for r in weather_rows:
        if not valid_prematch_weather_row(r):
            continue
        fid = r.get("forward_id") or ""
        if not fid:
            continue
        cur = weather_latest.get(fid)
        if cur is None or (r.get("captured_at_utc") or "") > (cur.get("captured_at_utc") or ""):
            weather_latest[fid] = r
    rotation_latest = {}
    for r in rotation_rows:
        fid = r.get("forward_id") or ""
        if not fid:
            continue
        cur = rotation_latest.get(fid)
        if cur is None or (r.get("captured_at_utc") or "") > (cur.get("captured_at_utc") or ""):
            rotation_latest[fid] = r

    latest_rows = []
    for bet in active:
        fid = bet.get("forward_id") or ""
        c = ctx.get(fid) or {}
        w = weather_latest.get(fid) or {}
        r = rotation_latest.get(fid) or {}
        latest_rows.append({
            "forward_id": fid,
            "rule": bet.get("rule") or "",
            "api_fixture_id": bet.get("api_fixture_id") or "",
            "home_team": c.get("home_team") or bet.get("home_team") or "",
            "away_team": c.get("away_team") or bet.get("away_team") or "",
            "kickoff_utc": c.get("current_kickoff_utc") or w.get("kickoff_utc") or "",
            "weather_snapshot_type": w.get("snapshot_type") or "",
            "weather_captured_at_utc": w.get("captured_at_utc") or "",
            "temperature_c": w.get("temperature_c") or "",
            "precipitation_probability_pct": w.get("precipitation_probability_pct") or "",
            "precipitation_mm": w.get("precipitation_mm") or "",
            "wind_speed_10m_kmh": w.get("wind_speed_10m_kmh") or "",
            "wind_gusts_10m_kmh": w.get("wind_gusts_10m_kmh") or "",
            "visibility_m": w.get("visibility_m") or "",
            "weather_code": w.get("weather_code") or "",
            "rotation_captured_at_utc": r.get("captured_at_utc") or "",
            "home_retained_starters": r.get("home_retained_starters") or "",
            "away_retained_starters": r.get("away_retained_starters") or "",
            "home_changed_starters": r.get("home_changed_starters") or "",
            "away_changed_starters": r.get("away_changed_starters") or "",
            "home_retained_pct": r.get("home_retained_pct") or "",
            "away_retained_pct": r.get("away_retained_pct") or "",
            "rotation_verified": "YES" if r.get("home_rotation_verified") == "YES" and r.get("away_rotation_verified") == "YES" else "NO",
            "context_only": "YES",
        })
    write_csv(LATEST, LATEST_FIELDS, latest_rows)

    meta = {
        "run_at_utc": iso(now),
        "status": "OK",
        "active_forward_rows": len(active),
        "new_weather_snapshots": new_weather,
        "total_weather_snapshots": len(weather_rows),
        "new_rotation_snapshots": new_rotation,
        "total_rotation_snapshots": len(rotation_rows),
        "geocoding_calls": geocoding_calls,
        "weather_calls": weather_calls,
        "air_quality_calls": air_quality_calls,
        "current_lineup_calls": current_lineup_calls,
        "previous_lineup_calls": previous_lineup_calls,
        "warnings": warnings,
        "policy": {
            "role": "context-only; never changes R1/R2/R3 eligibility",
            "weather": "Open-Meteo city-level proxy nearest hourly forecast to kickoff; timestamped snapshots",
            "weather_evidence_time": "PREMATCH_FROZEN only when captured_at_utc < kickoff_utc; post-kickoff rows are never prematch-usable",
            "postmatch_weather": "POSTMATCH_FACTUAL may exist only for research/audit and is excluded from prematch latest views",
            "rotation": "official current XI compared only with official previous-match XI",
            "missing_previous_xi": "rotation metrics left blank; never inferred",
            "xi_polling": "only inside final 90 minutes; workflow cadence handles re-checks until official XI appears",
        },
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
