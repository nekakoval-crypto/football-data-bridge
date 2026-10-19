import argparse
import csv
import json
import math
import os
import tempfile
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("PBK35_ROOT", Path(__file__).resolve().parent))
OPS = ROOT / "PBK35_DATA" / "ops"
ARCHIVE = OPS / "weather_snapshots.csv"
UNIVERSE = OPS / "pbk16_capture_universe.csv"

HOURLY = [
    "temperature_2m", "apparent_temperature",
    "relative_humidity_2m", "dew_point_2m",
    "surface_pressure", "cloud_cover",
    "precipitation_probability", "precipitation",
    "rain", "showers", "snowfall", "weather_code",
    "visibility", "wind_speed_10m",
    "wind_gusts_10m", "wind_direction_10m",
]

MAPPING = {
    "temperature_c": "temperature_2m",
    "apparent_temperature_c": "apparent_temperature",
    "relative_humidity_pct": "relative_humidity_2m",
    "dew_point_c": "dew_point_2m",
    "surface_pressure_hpa": "surface_pressure",
    "cloud_cover_pct": "cloud_cover",
    "precipitation_probability_pct": "precipitation_probability",
    "precipitation_mm": "precipitation",
    "rain_mm": "rain",
    "showers_mm": "showers",
    "snowfall_cm": "snowfall",
    "weather_code": "weather_code",
    "visibility_m": "visibility",
    "wind_speed_10m_kmh": "wind_speed_10m",
    "wind_gusts_10m_kmh": "wind_gusts_10m",
    "wind_direction_10m_deg": "wind_direction_10m",
}

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])

def utc(value):
    s = str(value or "").strip()
    if not s:
        raise ValueError("empty UTC timestamp")
    result = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone missing")
    return result.astimezone(timezone.utc)

def iso(value):
    return value.isoformat(timespec="seconds")

def due(done, fid, kickoff, now):
    h = (kickoff - now).total_seconds() / 3600
    if h <= 0:
        return None
    if 0 < h <= 72 and (fid, "BASELINE") not in done:
        return "BASELINE"
    if 6 < h <= 30 and (fid, "T24") not in done:
        return "T24"
    if 1.5 < h <= 6 and (fid, "T3") not in done:
        return "T3"
    if 0 < h <= 1.5 and (fid, "T60") not in done:
        return "T60"
    return None

def get_forecast(lat, lon, kickoff):
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY),
        "forecast_days": 16,
        "timezone": "UTC",
        "wind_speed_unit": "kmh",
    })
    url = "https://api.open-meteo.com/v1/forecast?" + params
    req = urllib.request.Request(
        url, headers={"User-Agent": "PBK35-weather-only/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if urllib.parse.urlparse(resp.geturl()).hostname != "api.open-meteo.com":
            raise RuntimeError("unexpected forecast provider redirect")
        data = json.load(resp)

    if data.get("error"):
        raise RuntimeError(str(data.get("reason", "provider error")))

    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        raise RuntimeError("no hourly timestamps")

    candidates = []
    for idx, raw in enumerate(times):
        t = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
        delta = abs((t - kickoff).total_seconds()) / 60
        candidates.append((delta, idx, t))

    gap, idx, selected = min(candidates)
    if gap > 90:
        raise RuntimeError("forecast farther than 90 minutes from kickoff")

    result = {}
    for field in HOURLY:
        values = hourly.get(field) or []
        result[field] = values[idx] if idx < len(values) else None
    return result, selected, gap

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-calls", type=int, default=4)
    args = parser.parse_args()

    if not 0 <= args.max_calls <= 4:
        raise RuntimeError("first-run budget limited to 0..4")

    rows, fields = read_csv(ARCHIVE)
    fixtures, fixture_fields = read_csv(UNIVERSE)
    if len(rows) < 289 or not fixtures:
        raise RuntimeError("unexpected archive/universe baseline")

    required = set(MAPPING) | {
        "forward_id", "api_fixture_id", "snapshot_type",
        "captured_at_utc", "kickoff_utc", "forecast_time_utc",
        "forecast_gap_minutes", "latitude", "longitude",
        "evidence_time_status", "usable_for_prematch",
        "source", "context_only", "notes"
    }
    if not required <= set(fields):
        raise RuntimeError("weather schema incompatible: " +
                           str(sorted(required - set(fields))))

    active_ids = {
        str(r.get("api_fixture_id") or "").strip()
        for r in fixtures
    }
    if not all(active_ids):
        raise RuntimeError("universe fixture identity unavailable")
    if len(active_ids) != len(fixtures):
        raise RuntimeError("duplicate active fixture ID")

    by_fixture = defaultdict(list)
    done = set()
    for row in rows:
        fid = str(row.get("api_fixture_id") or "").strip()
        by_fixture[fid].append(row)
        done.add((str(row.get("forward_id") or ""),
                  str(row.get("snapshot_type") or "")))

    now = datetime.now(timezone.utc)
    due_jobs = []
    blocked = []


    import unicodedata

    def normalize_city(value):
        value = unicodedata.normalize(
            "NFKD", str(value or "").strip().casefold()
        )
        return " ".join(
            "".join(
                c for c in value
                if not unicodedata.combining(c)
            ).split()
        )

    countries = {
        "austria": "AT", "belgium": "BE",
        "denmark": "DK", "england": "GB",
        "france": "FR", "germany": "DE",
        "italy": "IT", "latvia": "LV",
        "lithuania": "LT", "netherlands": "NL",
        "norway": "NO", "poland": "PL",
        "portugal": "PT", "scotland": "GB",
        "spain": "ES", "turkey": "TR",
    }

    context_rows, _ = read_csv(
        OPS / "pbk35_verified_venue_context_612.csv"
    )

    source_root = os.environ.get("PBK35_SOURCE_ROOT")
    if not source_root:
        raise RuntimeError("PBK35_SOURCE_ROOT_REQUIRED")
    main_root = Path(source_root)
    round_rows, _ = read_csv(
        main_root / "ops/current_round_fixtures.csv"
    )

    with (
        OPS / "pbk35_verified_coordinate_index_v1.json"
    ).open(encoding="utf-8") as stream:
        coordinate_index = json.load(stream)["entries"]

    fixtures_by_id = {
        str(r.get("api_fixture_id") or "").strip(): r
        for r in fixtures
    }
    contexts_by_id = {
        str(r.get("api_fixture_id") or "").strip(): r
        for r in context_rows
    }

    if len(fixtures_by_id) != len(fixtures):
        raise RuntimeError("DUPLICATE_FIXTURE_ID")
    if len(contexts_by_id) != len(context_rows):
        raise RuntimeError("DUPLICATE_VERIFIED_CONTEXT")

    rounds_by_id = {}
    for event in round_rows:
        key = str(event.get("fixture_id") or "").strip()
        rounds_by_id.setdefault(key, []).append(event)

    new_fixture_geo_ready = 0
    geocode_calls = 0
    geocode_added = 0

    for fid in sorted(active_ids):
        historical = by_fixture.get(fid, [])

        if not historical:
            fixture = fixtures_by_id[fid]
            verified = contexts_by_id.get(fid)
            events = [
                r for r in rounds_by_id.get(fid, [])
                if str(r.get("status") or "").lower()
                   == "scheduled"
            ]

            if not verified or len(events) != 1:
                blocked.append((fid, "VENUE_NOT_VERIFIED"))
                continue

            event = events[0]
            city = normalize_city(verified.get("venue_city"))
            event_city = normalize_city(event.get("venue_city"))
            country = countries.get(
                normalize_city(fixture.get("country"))
            )

            try:
                identity_ok = all((
                    bool(country),
                    bool(city),
                    city == event_city,
                    bool(event.get("venue_name")),
                    str(fixture.get("forward_id") or "")
                        == "CAPTURE|" + fid,
                    str(fixture.get("home_team_id") or "")
                        == str(event.get("home_team_id") or ""),
                    str(fixture.get("away_team_id") or "")
                        == str(event.get("away_team_id") or ""),
                    utc(fixture["kickoff_utc"])
                        == utc(event["kickoff_utc"]),
                    utc(fixture["kickoff_utc"])
                        == utc(verified["current_kickoff_utc"]),
                ))
            except (KeyError, ValueError, TypeError):
                identity_ok = False

            if not identity_ok:
                blocked.append((fid, "FIXTURE_GEOGRAPHY_CONFLICT"))
                continue

            proxy = coordinate_index.get(country + "|" + city)

            # PBK700_DYNAMIC_GEOCODING
            # Only independently verified fixture geography reaches here.
            # Never geocode in dry-run and never use stadium claims.
            if proxy is None:
                from urllib.parse import urlencode
                from urllib.request import urlopen
                from urllib.error import URLError

                if not args.live:
                    blocked.append((fid, "NEW_CITY_GEOCODE_PENDING_LIVE"))
                    continue

                # Avoid requests for fixtures outside a weather stage.
                if not due(
                    done, "CAPTURE|" + fid,
                    utc(fixture["kickoff_utc"]), now
                ):
                    blocked.append((fid, "NO_DUE_WEATHER_STAGE"))
                    continue

                if geocode_calls >= 2:
                    blocked.append((fid, "GEOCODE_BUDGET_EXHAUSTED"))
                    continue

                geocode_calls += 1
                from urllib.parse import quote

                query = urlencode({
                    "name": verified["venue_city"],
                    "count": 20,
                    "language": "en",
                    "format": "json",
                    "countryCode": country,
                })
                url = (
                    "https://geocoding-api.open-meteo.com"
                    "/v1/search?" + query
                )

                try:
                    with urlopen(url, timeout=12) as response:
                        payload = json.load(response)
                except (OSError, ValueError, URLError) as exc:
                    blocked.append((
                        fid, "GEOCODE_REQUEST_FAILED:"
                        + type(exc).__name__
                    ))
                    continue

                exact = [
                    item for item in payload.get("results", [])
                    if item.get("country_code") == country
                    and normalize_city(item.get("name")) == city
                ]

                # No first-result guessing. Distinct locations
                # with the same name require independent evidence.
                unique = {
                    (
                        round(float(item["latitude"]), 5),
                        round(float(item["longitude"]), 5)
                    )
                    for item in exact
                    if item.get("latitude") is not None
                    and item.get("longitude") is not None
                }

                if len(unique) != 1:
                    blocked.append((
                        fid, "GEOCODE_NOT_UNAMBIGUOUS:"
                        + str(len(unique))
                    ))
                    continue

                lat0, lon0 = next(iter(unique))
                if not (
                    math.isfinite(lat0) and math.isfinite(lon0)
                    and -90 <= lat0 <= 90
                    and -180 <= lon0 <= 180
                ):
                    blocked.append((fid, "GEOCODE_INVALID_COORDINATES"))
                    continue

                proxy = {
                    "country_code": country,
                    "normalized_city": city,
                    "venue_city": verified["venue_city"],
                    "latitude": lat0,
                    "longitude": lon0,
                    "evidence_fixture_ids": [fid],
                    "evidence_kind": "VERIFIED_CITY_PROXY",
                    "coordinate_source": "OPEN_METEO_GEOCODING",
                    "stadium_coordinates_verified": False,
                    "predictive_authority": "NOT_AUTHORIZED",
                    "betting_authority": False,
                }

                # Persist the new city once; future fixtures reuse it.
                import os as _os
                import tempfile as _tempfile

                geo_path = (
                    OPS / "pbk35_verified_coordinate_index_v1.json"
                )
                with geo_path.open(encoding="utf-8") as stream:
                    geo_data = json.load(stream)

                key = country + "|" + city

                if key in geo_data["entries"]:
                    blocked.append((fid, "GEO_INDEX_CHANGED"))
                    continue

                geo_data["entries"][key] = proxy
                geo_data["reusable_cities"] = len(
                    geo_data["entries"]
                )

                fd, temp_name = _tempfile.mkstemp(
                    prefix="pbk700_",
                    suffix=".tmp",
                    dir=str(OPS)
                )
                try:
                    with _os.fdopen(
                        fd, "w", encoding="utf-8"
                    ) as out:
                        json.dump(
                            geo_data, out,
                            ensure_ascii=False, indent=2
                        )
                        out.flush()
                        _os.fsync(out.fileno())
                    _os.replace(temp_name, geo_path)
                finally:
                    if _os.path.exists(temp_name):
                        _os.unlink(temp_name)

                coordinate_index[key] = proxy
                geocode_added += 1

            if not proxy:
                blocked.append((fid, "CITY_COORDINATES_UNAVAILABLE"))
                continue

            try:
                lat = float(proxy["latitude"])
                lon = float(proxy["longitude"])

                proxy_ok = (
                    math.isfinite(lat)
                    and math.isfinite(lon)
                    and -90 <= lat <= 90
                    and -180 <= lon <= 180
                    and proxy.get("country_code") == country
                    and proxy.get("normalized_city") == city
                    and proxy.get("evidence_kind")
                        == "VERIFIED_CITY_PROXY"
                    and proxy.get("stadium_coordinates_verified")
                        is False
                )
            except (KeyError, ValueError, TypeError):
                proxy_ok = False

            if not proxy_ok:
                blocked.append((fid, "CITY_PROXY_INVALID"))
                continue

            base = {
                "forward_id": "CAPTURE|" + fid,
                "rule": fixture.get("rule") or "",
                "api_fixture_id": fid,
                "kickoff_utc": fixture["kickoff_utc"],
                "venue_name": event["venue_name"],
                "venue_city": verified["venue_city"],
                "geocoded_name": proxy["venue_city"],
                "country_code": country,
                "latitude": lat,
                "longitude": lon,
                "elevation_source": "CITY_PROXY_NOT_STADIUM",
                "source": "verified city proxy",
            }

            historical = [base]
            new_fixture_geo_ready += 1

        valid = sorted(
            historical,
            key=lambda r: r.get("captured_at_utc") or "",
            reverse=True
        )
        base = valid[0]
        forward_id = str(base.get("forward_id") or "").strip()
        if not forward_id:
            blocked.append((fid, "MISSING_FORWARD_ID"))
            continue

        try:
            kickoff = utc(base["kickoff_utc"])
            lat = float(base["latitude"])
            lon = float(base["longitude"])
            if not (
                math.isfinite(lat) and math.isfinite(lon)
                and -90 <= lat <= 90 and -180 <= lon <= 180
            ):
                raise ValueError("invalid archived coordinates")
            if len({
                r.get("kickoff_utc") for r in historical
                if r.get("kickoff_utc")
            }) != 1:
                raise ValueError("conflicting archived kickoff")
        except (ValueError, KeyError) as exc:
            blocked.append((fid, "ARCHIVE_IDENTITY_CONFLICT:" + str(exc)))
            continue

        # No new fixture is inferred from a home team's stadium.
        stage = due(done, forward_id, kickoff, now)
        if stage:
            due_jobs.append((fid, stage, kickoff, lat, lon, base))

    print("PBK671 WEATHER-ONLY")
    print("MODE =", "LIVE" if args.live else "DRY_RUN")
    print("CURRENT FIXTURES =", len(active_ids))
    print("ARCHIVED WEATHER ROWS =", len(rows))
    print("DUE SNAPSHOTS =", len(due_jobs))
    print("BLOCKED IDENTITIES =", len(blocked))
    print("NEW FIXTURE GEO READY =", new_fixture_geo_ready)
    print("GEOCODE API CALLS =", geocode_calls)
    print("NEW CITY COORDINATES =", geocode_added)
    print("STAGE COUNTS =", dict(Counter(x[1] for x in due_jobs)))
    for fid, why in blocked[:10]:
        print("BLOCKED =", fid, why)

    if not args.live:
        print("DRY_RUN = NO NETWORK / NO WRITES")
        return

    new_rows = []
    failures = []
    calls = 0

    for fid, stage, kickoff, lat, lon, base in due_jobs:
        if calls >= args.max_calls:
            break
        if datetime.now(timezone.utc) >= kickoff:
            failures.append((fid, "KICKOFF_ALREADY_STARTED"))
            continue

        calls += 1
        try:
            forecast, timepoint, gap = get_forecast(lat, lon, kickoff)
            captured = datetime.now(timezone.utc)
            if captured >= kickoff:
                raise RuntimeError("post-kickoff capture forbidden")

            row = {field: "" for field in fields}
            row.update({
                key: base.get(key, "")
                for key in fields
                if key not in MAPPING
            })
            row["snapshot_type"] = stage
            row["captured_at_utc"] = iso(captured)
            row["hours_to_kickoff"] = (
                f"{(kickoff-captured).total_seconds()/3600:.2f}"
            )
            row["forecast_time_utc"] = iso(timepoint)
            row["forecast_gap_minutes"] = f"{gap:.1f}"
            row["evidence_time_status"] = "PREMATCH_FROZEN"
            row["usable_for_prematch"] = "true"
            row["context_only"] = "YES"
            row["source"] = "Open-Meteo weather; archived verified city proxy"
            row["notes"] = (
                "weather-only context; city proxy; "
                "no predictive or betting authority"
            )
            row["air_quality_status"] = "NOT_QUERIED_THIS_RUN"
            for name in (
                "air_quality_time_utc", "air_quality_gap_minutes",
                "dust_ug_m3", "pm10_ug_m3", "pm2_5_ug_m3",
                "aerosol_optical_depth", "european_aqi"
            ):
                if name in fields:
                    row[name] = ""

            for output, inp in MAPPING.items():
                value = forecast.get(inp)
                row[output] = "" if value is None else value

            if "thunderstorm_evidence" in fields:
                code = forecast.get("weather_code")
                row["thunderstorm_evidence"] = (
                    "YES" if code in (95, 96, 99) else "NO"
                )

            if row.get("temperature_c", "") == "":
                raise RuntimeError("forecast lacks temperature")

            new_rows.append(row)
            print("CAPTURED =", fid, stage, "GAP_MIN =", gap)

        except Exception as exc:
            failures.append((fid, str(exc)))
            print("FAILED =", fid, str(exc))

    if new_rows:
        # Atomic replacement preserves all previous rows.
        # The new file is published only after complete serialization.
        fd, temporary = tempfile.mkstemp(
            prefix="weather_snapshots_", suffix=".tmp",
            dir=str(OPS)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=fields, extrasaction="raise"
                )
                writer.writeheader()
                writer.writerows(rows + new_rows)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, ARCHIVE)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    print("OPEN_METEO_CALLS =", calls)
    print("NEW WEATHER SNAPSHOTS =", len(new_rows))
    print("TOTAL WEATHER SNAPSHOTS =", len(rows) + len(new_rows))
    print("FAILURES =", len(failures))
    print("XI / API_FOOTBALL CALLS = 0")
    if failures:
        raise RuntimeError("weather capture incomplete: " + str(failures))

if __name__ == "__main__":
    main()

