#!/usr/bin/env python3
"""PBK #273 — postmatch environmental factual/proxy research rail.

Purpose:
- retrospectively join finished PBK16 fixtures with postmatch environmental
  condition evidence and actual match mechanisms;
- support hypothesis generation such as rain -> long shots / saves / corners;
- never relabel retrospective weather as information known prematch.

Current weather implementation uses Open-Meteo Historical Forecast, explicitly
classified as HISTORICAL_FORECAST_ASSIMILATION_PROXY rather than a direct
stadium observation.

Research-only. No prediction, betting, value, stake or forward authority.
"""
from __future__ import annotations

import csv
import html
import json
import math
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPS = Path(os.getenv("OPS_DIR", str(ROOT / "ops")))
CONFIG = ROOT / "config" / "pbk_environmental_postmatch_research_v1.json"

FIXTURES = OPS / "historical_fixtures.csv"
TEAM_STATS = OPS / "team_match_statistics.csv"
EVENTS = OPS / "match_event_snapshots.csv"
VENUES = OPS / "pbk16_venue_registry.csv"

SNAPSHOTS = OPS / "environmental_postmatch_condition_snapshots.csv"
GEOCACHE = OPS / "environmental_postmatch_venue_geocache.csv"
DATASET = OPS / "environmental_postmatch_mechanism_dataset.csv"
META = OPS / "stage273_environmental_postmatch_last_run.json"

MAX_FIXTURES_PER_RUN = int(os.getenv("STAGE273_MAX_FIXTURES_PER_RUN", "24"))
HTTP_TIMEOUT = float(os.getenv("STAGE273_HTTP_TIMEOUT", "30"))
HTTP_ATTEMPTS = int(os.getenv("STAGE273_HTTP_ATTEMPTS", "3"))
HTTP_RETRY_DELAY = float(os.getenv("STAGE273_HTTP_RETRY_DELAY", "0.75"))
USER_AGENT = "PBK-stage273/1.0"
GEOCODE_RESOLVER_VERSION = "PBK_GEOCODE_V4"
GEOCODE_REPAIR_DISTANCE_KM = 25.0
GEOCODE_LEGACY_REVALIDATE_PER_RUN = int(
    os.getenv("STAGE273_GEOCODE_LEGACY_REVALIDATE_PER_RUN", "12")
)

SNAPSHOT_FIELDS = [
    "fixture_id","provider_league_id","league_name","season","round",
    "kickoff_utc","home_team","away_team","home_goals","away_goals",
    "venue_id","venue_name","venue_city","latitude","longitude",
    "geocode_quality_status","geocode_resolver_version",
    "captured_at_utc","source_class","source_name","source_url",
    "evidence_time_status","usable_for_prematch",
    "window_start_utc","window_end_utc","hourly_points",
    "temperature_mean_c","temperature_min_c","temperature_max_c",
    "apparent_temperature_mean_c","relative_humidity_mean_pct",
    "dew_point_mean_c","surface_pressure_mean_hpa",
    "precipitation_sum_mm","rain_sum_mm","showers_sum_mm","snowfall_sum_cm",
    "weather_code_mode","visibility_min_m",
    "wind_speed_mean_kmh","wind_speed_max_kmh",
    "wind_gust_mean_kmh","wind_gust_max_kmh",
    "wind_direction_mean_deg",
    "research_only","predictive_authority","betting_authority",
    "probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation",
]

GEOCACHE_FIELDS = [
    "venue_id","venue_name","venue_city","team_country",
    "latitude","longitude","elevation_m",
    "geocoded_name","geocoded_country","geocoded_country_code",
    "geocoded_admin1","geocoded_population","geocoded_feature_code",
    "geocode_quality_status","geocode_name_match_quality",
    "geocode_query_used","resolver_version",
    "captured_at_utc","source",
]

DATASET_FIELDS = [
    "fixture_id","provider_league_id","league_name","season","round",
    "kickoff_utc","home_team","away_team","home_goals","away_goals",
    "goals_total",
    "venue_id","venue_name","surface_provider","roof_type",
    "environment_source_class","environment_usable_for_prematch",
    "environment_geocode_quality_status","environment_geocode_resolver_version",
    "temperature_mean_c","apparent_temperature_mean_c",
    "relative_humidity_mean_pct","dew_point_mean_c",
    "surface_pressure_mean_hpa",
    "precipitation_sum_mm","rain_sum_mm","showers_sum_mm","snowfall_sum_cm",
    "visibility_min_m","wind_speed_mean_kmh","wind_speed_max_kmh",
    "wind_gust_mean_kmh","wind_gust_max_kmh","weather_code_mode",
    "shots_total","shots_on_goal_total","shots_outsidebox_total",
    "goalkeeper_saves_total","corners_total",
    "passes_accuracy_mean","expected_goals_total",
    "normal_goals","penalty_goals","own_goals",
    "red_card_events","var_events",
    "goalkeeper_error_evidence",
    "mechanism_coverage_status",
    "causal_claim_authorized","research_only","predictive_authority",
    "betting_authority","probability_mutation","eligibility_mutation",
    "stake_changes","forward_journal_mutation",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except (TypeError, ValueError):
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


def write_csv_atomic(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def fnum(value: Any) -> float | None:
    try:
        x = float(str(value).strip())
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}".rstrip("0").rstrip(".")


def isum(value: Any) -> int:
    try:
        return int(float(str(value or "0").strip()))
    except (TypeError, ValueError):
        return 0


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def safe_min(values: list[float]) -> float | None:
    return min(values) if values else None


def safe_max(values: list[float]) -> float | None:
    return max(values) if values else None


def circular_mean_degrees(values: list[float]) -> float | None:
    if not values:
        return None
    sin_sum = sum(math.sin(math.radians(v)) for v in values)
    cos_sum = sum(math.cos(math.radians(v)) for v in values)
    if sin_sum == 0 and cos_sum == 0:
        return None
    return (math.degrees(math.atan2(sin_sum, cos_sum)) + 360.0) % 360.0


def mode_code(values: list[int]) -> str:
    if not values:
        return ""
    counts = Counter(values)
    return str(sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0])


def http_json(
    url: str,
    params: dict[str, Any],
    *,
    attempts: int | None = None,
    retry_delay: float | None = None,
) -> dict[str, Any]:
    """GET JSON with bounded retry for transient research-source failures."""
    attempts = HTTP_ATTEMPTS if attempts is None else attempts
    retry_delay = HTTP_RETRY_DELAY if retry_delay is None else retry_delay

    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    query = urllib.parse.urlencode(params)
    target = f"{url}?{query}"
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            target,
            headers={"User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError("unexpected non-object API response")
            return payload
        except Exception as exc:
            last_error = exc
            if attempt >= attempts:
                break
            if retry_delay > 0:
                time.sleep(retry_delay * attempt)

    raise RuntimeError(
        f"HTTP JSON failed after {attempts} attempts: {target}: {last_error}"
    ) from last_error


def validate_contract(config: dict[str, Any]) -> None:
    if config.get("research_id") != "PBK_ENVIRONMENTAL_POSTMATCH_FACTUAL_V1":
        raise ValueError("research id drift")
    if config.get("status") != "RESEARCH_ONLY":
        raise ValueError("status drift")
    if config.get("authority") != "RESEARCH":
        raise ValueError("authority drift")

    source = config.get("source_policy") or {}
    if source.get("implemented_weather_source_class") != "HISTORICAL_FORECAST_ASSIMILATION_PROXY":
        raise ValueError("source class drift")
    if source.get("historical_proxy_is_direct_stadium_observation") is not False:
        raise ValueError("proxy cannot be direct observation")
    if source.get("historical_proxy_is_prematch_forecast") is not False:
        raise ValueError("postmatch proxy cannot be relabeled prematch")
    if source.get("usable_for_prematch") is not False:
        raise ValueError("postmatch source cannot be prematch-usable")

    guards = config.get("guards") or {}
    for key in [
        "postmatch_only",
        "finished_fixture_required",
        "both_team_statistics_required",
        "no_causal_claim_from_single_match",
        "no_predictive_authority",
        "no_betting_authority",
        "no_probability_mutation",
        "no_eligibility_mutation",
        "no_value_or_ev",
        "no_stake_changes",
        "no_forward_journal_mutation",
        "never_relabel_as_prematch_known",
        "unknown_not_zero",
    ]:
        if guards.get(key) is not True:
            raise ValueError(f"guard drift: {key}")


def finished_fixtures(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Normalize canonical Stage80 historical fixture rows for Stage273.

    Current Stage80 schema uses:
    terminal_observed / latest_source_status / latest_kickoff_utc /
    final_score_home / final_score_away.
    """
    out = {}

    for source_row in rows:
        fixture_id = str(source_row.get("fixture_id") or "").strip()
        if not fixture_id:
            continue

        terminal = str(
            source_row.get("terminal_observed")
            or source_row.get("is_finished")
            or ""
        ).strip().upper()

        source_status = str(
            source_row.get("latest_source_status")
            or source_row.get("source_status")
            or ""
        ).strip().upper()

        kickoff = (
            source_row.get("latest_kickoff_utc")
            or source_row.get("kickoff_utc")
            or source_row.get("first_kickoff_utc")
            or ""
        )

        if terminal not in {"YES", "TRUE", "1"}:
            continue

        if source_status not in {"FT", "AET", "PEN"}:
            continue

        if parse_iso(kickoff) is None:
            continue

        row = dict(source_row)
        row["kickoff_utc"] = str(kickoff)
        row["source_status"] = source_status
        row["home_goals"] = str(
            source_row.get("final_score_home")
            if source_row.get("final_score_home") not in {None, ""}
            else source_row.get("home_goals") or ""
        )
        row["away_goals"] = str(
            source_row.get("final_score_away")
            if source_row.get("final_score_away") not in {None, ""}
            else source_row.get("away_goals") or ""
        )

        out[fixture_id] = row

    return out


def complete_team_stats(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        fixture_id = str(row.get("fixture_id") or "").strip()
        side = str(row.get("side") or "").strip().upper()
        if fixture_id and side in {"HOME","AWAY"}:
            grouped[fixture_id].append(row)

    out = {}
    for fixture_id, group in grouped.items():
        sides = {str(r.get("side") or "").strip().upper() for r in group}
        if {"HOME","AWAY"} <= sides:
            by_side = {}
            for r in group:
                by_side[str(r.get("side") or "").strip().upper()] = r
            out[fixture_id] = [by_side["HOME"], by_side["AWAY"]]
    return out


def venue_by_team(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        str(row.get("team_id") or "").strip(): row
        for row in rows
        if str(row.get("team_id") or "").strip()
    }


COUNTRY_CODE_BY_TEAM_COUNTRY = {
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "france": "FR",
    "germany": "DE",
    "spain": "ES",
    "italy": "IT",
    "austria": "AT",
    "belgium": "BE",
    "denmark": "DK",
    "lithuania": "LT",
    "latvia": "LV",
    "netherlands": "NL",
    "norway": "NO",
    "poland": "PL",
    "portugal": "PT",
    "turkey": "TR",
    "turkiye": "TR",
}

CITY_ALIASES = {
    "wien": "Vienna",
    "munchen": "Munich",
    "koln": "Cologne",
    "firenze": "Florence",
    "roma": "Rome",
    "torino": "Turin",
    "venezia": "Venice",
    "milano": "Milan",
    "brugge": "Bruges",
    "gent": "Ghent",
    "bruxelles brussel": "Brussels",
    "la haye": "The Hague",
    "lyngby": "Kongens Lyngby",
    "villarreal": "Vila-real",
    "kocaeli": "Izmit",
    "sevilla": "Seville",
    "donostia san sebastian": "San Sebastian",
    "ilha da madeira": "Madeira",
}

PLACE_TRANSLITERATION = str.maketrans({
    "ł": "l", "Ł": "L",
    "ø": "o", "Ø": "O",
    "đ": "d", "Đ": "D",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "Th",
    "æ": "ae", "Æ": "Ae",
    "œ": "oe", "Œ": "Oe",
    "ı": "i",
})

LOCALITY_FEATURE_RANK = {
    "PPLC": 5,
    "PPLA": 4,
    "PPLA2": 3,
    "PPLA3": 2,
    "PPL": 1,
}


def normalize_place(value: Any) -> str:
    text = html.unescape(str(value or "")).strip()
    text = text.translate(PLACE_TRANSLITERATION).casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def city_query_variants(city: str) -> list[str]:
    cleaned = html.unescape(str(city or "")).strip()
    if not cleaned:
        return []

    variants = [cleaned]
    if "," in cleaned:
        variants.append(cleaned.split(",", 1)[0].strip())

    normalized = normalize_place(cleaned)
    alias = CITY_ALIASES.get(normalized)
    if alias:
        variants.append(alias)

    if normalized.startswith("ilha da "):
        variants.append(cleaned[8:].strip())

    out = []
    seen = set()
    for value in variants:
        key = normalize_place(value)
        if value and key and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def country_code_for_venue(venue: dict[str, str]) -> str:
    return COUNTRY_CODE_BY_TEAM_COUNTRY.get(
        normalize_place(venue.get("team_country")),
        "",
    )


def candidate_name_quality(candidate_name: Any, query_variants: list[str]) -> int:
    candidate = normalize_place(candidate_name)
    if not candidate:
        return 0
    candidate_tokens = set(candidate.split())

    best = 0
    for variant in query_variants:
        target = normalize_place(variant)
        if not target:
            continue
        if candidate == target:
            best = max(best, 3)
            continue
        target_tokens = set(target.split())
        if target_tokens and (
            target_tokens.issubset(candidate_tokens)
            or candidate_tokens.issubset(target_tokens)
        ):
            best = max(best, 2)
    return best


def candidate_country_ok(candidate: dict[str, Any], venue: dict[str, str]) -> bool:
    expected_code = country_code_for_venue(venue)
    candidate_code = str(candidate.get("country_code") or "").strip().upper()

    if expected_code and candidate_code:
        return candidate_code == expected_code

    expected_country = normalize_place(venue.get("team_country"))
    candidate_country = normalize_place(candidate.get("country"))

    if expected_country in {"england", "scotland", "wales", "northern ireland"}:
        return candidate_country in {
            "united kingdom",
            "england",
            "scotland",
            "wales",
            "northern ireland",
        }

    return bool(expected_country and candidate_country == expected_country)


def select_geocode_candidate(
    candidates: list[dict[str, Any]],
    venue: dict[str, str],
    query_variants: list[str],
) -> tuple[dict[str, Any] | None, int]:
    ranked = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if not candidate_country_ok(candidate, venue):
            continue
        lat = fnum(candidate.get("latitude"))
        lon = fnum(candidate.get("longitude"))
        if lat is None or lon is None:
            continue

        quality = candidate_name_quality(candidate.get("name"), query_variants)
        if quality < 2:
            continue

        feature_rank = LOCALITY_FEATURE_RANK.get(
            str(candidate.get("feature_code") or "").strip().upper(),
            0,
        )
        if feature_rank <= 0:
            continue
        population = fnum(candidate.get("population")) or 0.0
        ranked.append(
            (
                quality,
                feature_rank,
                population,
                candidate,
            )
        )

    if not ranked:
        return None, 0

    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    quality, _, _, candidate = ranked[0]
    return candidate, quality


def verified_geocache_by_venue(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        str(row.get("venue_id") or "").strip(): row
        for row in rows
        if str(row.get("venue_id") or "").strip()
        and str(row.get("resolver_version") or "") == GEOCODE_RESOLVER_VERSION
        and str(row.get("geocode_quality_status") or "") == "VERIFIED_LOCALITY_V4"
        and fnum(row.get("latitude")) is not None
        and fnum(row.get("longitude")) is not None
    }


def unresolved_geocache_venue_ids(rows: list[dict[str, str]]) -> set[str]:
    return {
        str(row.get("venue_id") or "").strip()
        for row in rows
        if str(row.get("venue_id") or "").strip()
        and str(row.get("resolver_version") or "") == GEOCODE_RESOLVER_VERSION
        and str(row.get("geocode_quality_status") or "") == "UNRESOLVED_V4"
    }


def unresolved_geocode_record(
    venue: dict[str, str],
    captured_at: datetime,
    queries: list[str],
) -> dict[str, str]:
    return {
        "venue_id": str(venue.get("venue_id") or "").strip(),
        "venue_name": str(venue.get("venue_name") or ""),
        "venue_city": html.unescape(str(venue.get("venue_city") or "")).strip(),
        "team_country": str(venue.get("team_country") or ""),
        "latitude": "",
        "longitude": "",
        "elevation_m": "",
        "geocoded_name": "",
        "geocoded_country": "",
        "geocoded_country_code": "",
        "geocoded_admin1": "",
        "geocoded_population": "",
        "geocoded_feature_code": "",
        "geocode_quality_status": "UNRESOLVED_V4",
        "geocode_name_match_quality": "0",
        "geocode_query_used": " | ".join(queries),
        "resolver_version": GEOCODE_RESOLVER_VERSION,
        "captured_at_utc": iso(captured_at),
        "source": "Open-Meteo Geocoding API city proxy v4",
    }


def geocode_venue(
    config: dict[str, Any],
    venue: dict[str, str],
    captured_at: datetime,
) -> dict[str, str] | None:
    city = html.unescape(str(venue.get("venue_city") or "")).strip()
    country = str(venue.get("team_country") or "").strip()
    venue_id = str(venue.get("venue_id") or "").strip()

    if not city or not venue_id:
        return None

    queries = city_query_variants(city)
    all_candidates = []

    for query in queries:
        payload = http_json(
            config["source_policy"]["geocoding_endpoint"],
            {
                "name": query,
                "count": 10,
                "language": "en",
                "format": "json",
            },
        )
        for result in payload.get("results") or []:
            if isinstance(result, dict):
                enriched = dict(result)
                enriched["_pbk_query"] = query
                all_candidates.append(enriched)

    result, quality = select_geocode_candidate(
        all_candidates,
        venue,
        queries,
    )
    if result is None:
        return None

    lat = fnum(result.get("latitude"))
    lon = fnum(result.get("longitude"))
    if lat is None or lon is None:
        return None

    return {
        "venue_id": venue_id,
        "venue_name": venue.get("venue_name") or "",
        "venue_city": city,
        "team_country": country,
        "latitude": fmt(lat),
        "longitude": fmt(lon),
        "elevation_m": fmt(fnum(result.get("elevation"))),
        "geocoded_name": str(result.get("name") or ""),
        "geocoded_country": str(result.get("country") or ""),
        "geocoded_country_code": str(result.get("country_code") or ""),
        "geocoded_admin1": str(result.get("admin1") or ""),
        "geocoded_population": fmt(fnum(result.get("population"))),
        "geocoded_feature_code": str(result.get("feature_code") or ""),
        "geocode_quality_status": "VERIFIED_LOCALITY_V4",
        "geocode_name_match_quality": str(quality),
        "geocode_query_used": str(result.get("_pbk_query") or ""),
        "resolver_version": GEOCODE_RESOLVER_VERSION,
        "captured_at_utc": iso(captured_at),
        "source": "Open-Meteo Geocoding API city proxy v4",
    }


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    radius_km = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2.0) ** 2
    )
    return radius_km * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def snapshot_geocode_drift_km(
    snapshot: dict[str, str],
    geo: dict[str, str],
) -> float | None:
    values = [
        fnum(snapshot.get("latitude")),
        fnum(snapshot.get("longitude")),
        fnum(geo.get("latitude")),
        fnum(geo.get("longitude")),
    ]
    if any(v is None for v in values):
        return None
    return haversine_km(values[0], values[1], values[2], values[3])


def venue_by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out = {}
    for row in rows:
        venue_id = str(row.get("venue_id") or "").strip()
        if venue_id and venue_id not in out:
            out[venue_id] = row
    return out


def legacy_geocache_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if str(row.get("venue_id") or "").strip()
        and str(row.get("resolver_version") or "") != GEOCODE_RESOLVER_VERSION
    ]


def parse_hour(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) == 16:
        text += ":00+00:00"
    elif text.endswith("Z"):
        text = text.replace("Z", "+00:00")
    elif "+" not in text[10:] and not text.endswith("+00:00"):
        text += "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def summarize_historical_weather(
    hourly: dict[str, Any],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, str] | None:
    times = hourly.get("time") or []
    indexes = []
    for idx, raw in enumerate(times):
        dt = parse_hour(raw)
        if dt and window_start <= dt <= window_end:
            indexes.append(idx)
    if not indexes:
        return None

    def nums(key: str) -> list[float]:
        arr = hourly.get(key) or []
        out = []
        for i in indexes:
            if i < len(arr):
                value = fnum(arr[i])
                if value is not None:
                    out.append(value)
        return out

    def ints(key: str) -> list[int]:
        arr = hourly.get(key) or []
        out = []
        for i in indexes:
            if i < len(arr):
                try:
                    out.append(int(float(arr[i])))
                except (TypeError, ValueError):
                    pass
        return out

    temp = nums("temperature_2m")
    apparent = nums("apparent_temperature")
    humidity = nums("relative_humidity_2m")
    dew = nums("dew_point_2m")
    pressure = nums("surface_pressure")
    precip = nums("precipitation")
    rain = nums("rain")
    showers = nums("showers")
    snow = nums("snowfall")
    visibility = nums("visibility")
    wind = nums("wind_speed_10m")
    gust = nums("wind_gusts_10m")
    direction = nums("wind_direction_10m")

    return {
        "hourly_points": str(len(indexes)),
        "temperature_mean_c": fmt(mean(temp)),
        "temperature_min_c": fmt(safe_min(temp)),
        "temperature_max_c": fmt(safe_max(temp)),
        "apparent_temperature_mean_c": fmt(mean(apparent)),
        "relative_humidity_mean_pct": fmt(mean(humidity)),
        "dew_point_mean_c": fmt(mean(dew)),
        "surface_pressure_mean_hpa": fmt(mean(pressure)),
        "precipitation_sum_mm": fmt(sum(precip)) if precip else "",
        "rain_sum_mm": fmt(sum(rain)) if rain else "",
        "showers_sum_mm": fmt(sum(showers)) if showers else "",
        "snowfall_sum_cm": fmt(sum(snow)) if snow else "",
        "weather_code_mode": mode_code(ints("weather_code")),
        "visibility_min_m": fmt(safe_min(visibility)),
        "wind_speed_mean_kmh": fmt(mean(wind)),
        "wind_speed_max_kmh": fmt(safe_max(wind)),
        "wind_gust_mean_kmh": fmt(mean(gust)),
        "wind_gust_max_kmh": fmt(safe_max(gust)),
        "wind_direction_mean_deg": fmt(circular_mean_degrees(direction)),
    }


def fetch_fixture_environment(
    config: dict[str, Any],
    fixture: dict[str, str],
    venue: dict[str, str],
    geo: dict[str, str],
    captured_at: datetime,
) -> dict[str, Any] | None:
    kickoff = parse_iso(fixture.get("kickoff_utc"))
    lat = fnum(geo.get("latitude"))
    lon = fnum(geo.get("longitude"))
    if not kickoff or lat is None or lon is None:
        return None

    source = config["source_policy"]
    before = int(source["match_window_minutes_before_kickoff"])
    after = int(source["match_window_minutes_after_kickoff"])
    start = kickoff - timedelta(minutes=before)
    end = kickoff + timedelta(minutes=after)

    variables = ",".join(config["weather_variables"])
    payload = http_json(
        source["historical_weather_endpoint"],
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": variables,
            "timezone": "UTC",
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
        },
    )

    summary = summarize_historical_weather(payload.get("hourly") or {}, start, end)
    if summary is None:
        return None

    row = {
        "fixture_id": fixture.get("fixture_id") or "",
        "provider_league_id": fixture.get("provider_league_id") or "",
        "league_name": fixture.get("league_name") or "",
        "season": fixture.get("season") or "",
        "round": fixture.get("round") or "",
        "kickoff_utc": fixture.get("kickoff_utc") or "",
        "home_team": fixture.get("home_team") or "",
        "away_team": fixture.get("away_team") or "",
        "home_goals": fixture.get("home_goals") or "",
        "away_goals": fixture.get("away_goals") or "",
        "venue_id": venue.get("venue_id") or "",
        "venue_name": venue.get("venue_name") or "",
        "venue_city": venue.get("venue_city") or "",
        "latitude": geo.get("latitude") or "",
        "longitude": geo.get("longitude") or "",
        "geocode_quality_status": geo.get("geocode_quality_status") or "",
        "geocode_resolver_version": geo.get("resolver_version") or "",
        "captured_at_utc": iso(captured_at),
        "source_class": source["implemented_weather_source_class"],
        "source_name": source["implemented_weather_source"],
        "source_url": source["historical_weather_endpoint"],
        "evidence_time_status": "POSTMATCH_FACTUAL_RESEARCH_PROXY",
        "usable_for_prematch": "false",
        "window_start_utc": iso(start),
        "window_end_utc": iso(end),
        "research_only": "true",
        "predictive_authority": "NOT_AUTHORIZED",
        "betting_authority": "NOT_AUTHORIZED",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }
    row.update(summary)
    return row


def event_metrics(events: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    out: dict[str, Counter] = defaultdict(Counter)
    for row in events:
        fixture_id = str(row.get("fixture_id") or "").strip()
        if not fixture_id:
            continue
        event_type = str(row.get("event_type") or "").strip().lower()
        detail = str(row.get("detail") or "").strip().lower()

        if event_type == "goal":
            if "penalty" in detail:
                out[fixture_id]["penalty_goals"] += 1
            elif "own goal" in detail:
                out[fixture_id]["own_goals"] += 1
            else:
                out[fixture_id]["normal_goals"] += 1

        if event_type == "card" and "red" in detail:
            out[fixture_id]["red_card_events"] += 1

        if event_type == "var":
            out[fixture_id]["var_events"] += 1

    return {k: dict(v) for k, v in out.items()}


def mechanism_projection(
    snapshots: list[dict[str, str]],
    stats_by_fixture: dict[str, list[dict[str, str]]],
    fixtures: dict[str, dict[str, str]],
    venue_by_team_id: dict[str, dict[str, str]],
    events: list[dict[str, str]],
) -> list[dict[str, Any]]:
    event_by_fixture = event_metrics(events)
    rows = []

    for env in snapshots:
        fixture_id = str(env.get("fixture_id") or "").strip()
        stats = stats_by_fixture.get(fixture_id)
        fixture = fixtures.get(fixture_id)
        if not stats or not fixture:
            continue

        home = next((r for r in stats if str(r.get("side") or "").upper() == "HOME"), None)
        away = next((r for r in stats if str(r.get("side") or "").upper() == "AWAY"), None)
        if not home or not away:
            continue

        venue = venue_by_team_id.get(str(home.get("team_id") or "").strip(), {})
        ev = event_by_fixture.get(fixture_id, {})

        def total(field: str) -> int:
            return isum(home.get(field)) + isum(away.get(field))

        pass_values = [fnum(home.get("passes_accuracy_pct")), fnum(away.get("passes_accuracy_pct"))]
        pass_values = [v for v in pass_values if v is not None]

        xg_values = [fnum(home.get("expected_goals")), fnum(away.get("expected_goals"))]
        xg_known = [v for v in xg_values if v is not None]

        home_goals = isum(fixture.get("home_goals"))
        away_goals = isum(fixture.get("away_goals"))

        row = {
            "fixture_id": fixture_id,
            "provider_league_id": fixture.get("provider_league_id") or "",
            "league_name": fixture.get("league_name") or "",
            "season": fixture.get("season") or "",
            "round": fixture.get("round") or "",
            "kickoff_utc": fixture.get("kickoff_utc") or "",
            "home_team": fixture.get("home_team") or "",
            "away_team": fixture.get("away_team") or "",
            "home_goals": str(home_goals),
            "away_goals": str(away_goals),
            "goals_total": str(home_goals + away_goals),

            "venue_id": venue.get("venue_id") or env.get("venue_id") or "",
            "venue_name": venue.get("venue_name") or env.get("venue_name") or "",
            "surface_provider": venue.get("surface_provider") or "",
            "roof_type": venue.get("roof_type") or "UNKNOWN",

            "environment_source_class": env.get("source_class") or "",
            "environment_usable_for_prematch": "false",
            "environment_geocode_quality_status": env.get("geocode_quality_status") or "",
            "environment_geocode_resolver_version": env.get("geocode_resolver_version") or "",

            "temperature_mean_c": env.get("temperature_mean_c") or "",
            "apparent_temperature_mean_c": env.get("apparent_temperature_mean_c") or "",
            "relative_humidity_mean_pct": env.get("relative_humidity_mean_pct") or "",
            "dew_point_mean_c": env.get("dew_point_mean_c") or "",
            "surface_pressure_mean_hpa": env.get("surface_pressure_mean_hpa") or "",
            "precipitation_sum_mm": env.get("precipitation_sum_mm") or "",
            "rain_sum_mm": env.get("rain_sum_mm") or "",
            "showers_sum_mm": env.get("showers_sum_mm") or "",
            "snowfall_sum_cm": env.get("snowfall_sum_cm") or "",
            "visibility_min_m": env.get("visibility_min_m") or "",
            "wind_speed_mean_kmh": env.get("wind_speed_mean_kmh") or "",
            "wind_speed_max_kmh": env.get("wind_speed_max_kmh") or "",
            "wind_gust_mean_kmh": env.get("wind_gust_mean_kmh") or "",
            "wind_gust_max_kmh": env.get("wind_gust_max_kmh") or "",
            "weather_code_mode": env.get("weather_code_mode") or "",

            "shots_total": str(total("shots_total")),
            "shots_on_goal_total": str(total("shots_on_goal")),
            "shots_outsidebox_total": str(total("shots_outsidebox")),
            "goalkeeper_saves_total": str(total("goalkeeper_saves")),
            "corners_total": str(total("corners")),
            "passes_accuracy_mean": fmt(mean(pass_values)),
            "expected_goals_total": fmt(sum(xg_known)) if len(xg_known) == 2 else "",

            "normal_goals": str(ev.get("normal_goals", 0)),
            "penalty_goals": str(ev.get("penalty_goals", 0)),
            "own_goals": str(ev.get("own_goals", 0)),
            "red_card_events": str(ev.get("red_card_events", 0)),
            "var_events": str(ev.get("var_events", 0)),

            "goalkeeper_error_evidence": "NOT_AVAILABLE_IN_CURRENT_EVENT_ARCHIVE",
            "mechanism_coverage_status": "TEAM_STATS_COMPLETE_EVENTS_AVAILABLE" if fixture_id in event_by_fixture else "TEAM_STATS_COMPLETE_EVENTS_MISSING",
            "causal_claim_authorized": "false",
            "research_only": "true",
            "predictive_authority": "NOT_AUTHORIZED",
            "betting_authority": "NOT_AUTHORIZED",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        }
        rows.append(row)

    rows.sort(key=lambda r: (r["kickoff_utc"], r["fixture_id"]))
    return rows


def run(captured_at: datetime | None = None) -> dict[str, Any]:
    captured_at = captured_at or utc_now()
    config = read_json(CONFIG)
    validate_contract(config)

    fixtures = finished_fixtures(read_csv(FIXTURES))
    stats = complete_team_stats(read_csv(TEAM_STATS))
    venue_rows = read_csv(VENUES)
    venues = venue_by_team(venue_rows)
    venues_by_id = venue_by_id(venue_rows)
    events = read_csv(EVENTS)

    existing_snapshots = read_csv(SNAPSHOTS)
    geocache_rows = read_csv(GEOCACHE)
    geocache = verified_geocache_by_venue(geocache_rows)
    unresolved_venues = unresolved_geocache_venue_ids(geocache_rows)

    diagnostics = Counter()
    geocache_updates = []
    repaired_snapshot_by_fixture = {}

    legacy_rows = legacy_geocache_rows(geocache_rows)
    diagnostics["legacy_geocache_rows_seen"] = len(legacy_rows)

    for legacy in legacy_rows[:GEOCODE_LEGACY_REVALIDATE_PER_RUN]:
        venue_id = str(legacy.get("venue_id") or "").strip()
        venue = venues_by_id.get(venue_id)
        if not venue:
            diagnostics["legacy_geocode_venue_registry_missing"] += 1
            continue

        try:
            resolved = geocode_venue(config, venue, captured_at)
            diagnostics["legacy_geocode_revalidation_calls"] += 1
        except Exception:
            diagnostics["legacy_geocode_revalidation_error"] += 1
            continue

        if not resolved:
            unresolved = unresolved_geocode_record(
                venue,
                captured_at,
                city_query_variants(venue.get("venue_city") or ""),
            )
            geocache_updates.append(unresolved)
            unresolved_venues.add(venue_id)
            diagnostics["legacy_geocode_unresolved_v2"] += 1
            continue

        geocache[venue_id] = resolved
        geocache_updates.append(resolved)
        diagnostics["legacy_geocode_verified_v2"] += 1

        for snapshot in existing_snapshots:
            if str(snapshot.get("venue_id") or "").strip() != venue_id:
                continue
            drift = snapshot_geocode_drift_km(snapshot, resolved)
            if drift is None or drift <= GEOCODE_REPAIR_DISTANCE_KM:
                continue

            fixture_id = str(snapshot.get("fixture_id") or "").strip()
            fixture = fixtures.get(fixture_id)
            if not fixture:
                diagnostics["snapshot_repair_fixture_missing"] += 1
                continue

            try:
                repaired = fetch_fixture_environment(
                    config,
                    fixture,
                    venue,
                    resolved,
                    captured_at,
                )
                diagnostics["snapshot_repair_weather_calls"] += 1
            except Exception:
                diagnostics["snapshot_repair_weather_error"] += 1
                continue

            if repaired:
                repaired_snapshot_by_fixture[fixture_id] = repaired
                diagnostics["snapshots_repaired_geocode_drift"] += 1

    if repaired_snapshot_by_fixture:
        existing_snapshots = [
            repaired_snapshot_by_fixture.get(
                str(row.get("fixture_id") or "").strip(),
                row,
            )
            for row in existing_snapshots
        ]

    snap_by_fixture = {
        str(r.get("fixture_id") or "").strip(): r
        for r in existing_snapshots
        if str(r.get("fixture_id") or "").strip()
    }

    eligible = []
    for fixture_id, pair in stats.items():
        fixture = fixtures.get(fixture_id)
        if not fixture or fixture_id in snap_by_fixture:
            continue
        home = next((r for r in pair if str(r.get("side") or "").upper() == "HOME"), None)
        if not home:
            continue
        venue = venues.get(str(home.get("team_id") or "").strip())
        if not venue:
            continue
        venue_id = str(venue.get("venue_id") or "").strip()
        if venue_id and venue_id in unresolved_venues:
            continue
        eligible.append((parse_iso(fixture.get("kickoff_utc")), fixture_id, fixture, venue))

    eligible.sort(key=lambda x: (x[0] or captured_at, x[1]))
    selected = eligible[:MAX_FIXTURES_PER_RUN]

    new_snapshots = []
    diagnostics["unresolved_v2_venues_skipped"] = len(unresolved_venues)

    for _, fixture_id, fixture, venue in selected:
        venue_id = str(venue.get("venue_id") or "").strip()
        geo = geocache.get(venue_id)

        if geo is None:
            try:
                geo = geocode_venue(config, venue, captured_at)
            except Exception:
                diagnostics["geocode_error"] += 1
                continue
            diagnostics["geocode_calls"] += 1
            if not geo:
                diagnostics["geocode_missing"] += 1
                unresolved = unresolved_geocode_record(
                    venue,
                    captured_at,
                    city_query_variants(venue.get("venue_city") or ""),
                )
                geocache_updates.append(unresolved)
                unresolved_venues.add(venue_id)
                continue
            geocache[venue_id] = geo
            geocache_updates.append(geo)
            diagnostics["geocode_verified_v2"] += 1
            time.sleep(0.15)

        try:
            env = fetch_fixture_environment(config, fixture, venue, geo, captured_at)
            diagnostics["weather_calls"] += 1
        except Exception:
            diagnostics["weather_error"] += 1
            continue

        if not env:
            diagnostics["weather_missing"] += 1
            continue

        new_snapshots.append(env)
        snap_by_fixture[fixture_id] = env
        diagnostics["snapshots_created"] += 1
        time.sleep(0.15)

    if geocache_updates:
        merged_geos = {
            str(r.get("venue_id") or ""): r
            for r in geocache_rows
            if str(r.get("venue_id") or "")
        }
        for r in geocache_updates:
            merged_geos[str(r.get("venue_id") or "")] = r
        write_csv_atomic(
            GEOCACHE,
            GEOCACHE_FIELDS,
            [merged_geos[k] for k in sorted(merged_geos)],
        )

    if new_snapshots or repaired_snapshot_by_fixture:
        all_snaps = existing_snapshots + new_snapshots
        write_csv_atomic(SNAPSHOTS, SNAPSHOT_FIELDS, all_snaps)
    elif not SNAPSHOTS.exists():
        write_csv_atomic(SNAPSHOTS, SNAPSHOT_FIELDS, existing_snapshots)

    dataset = mechanism_projection(
        read_csv(SNAPSHOTS),
        stats,
        fixtures,
        venues,
        events,
    )
    write_csv_atomic(DATASET, DATASET_FIELDS, dataset)

    source_counts = Counter(str(r.get("environment_source_class") or "") for r in dataset)
    coverage_counts = Counter(str(r.get("mechanism_coverage_status") or "") for r in dataset)

    meta = {
        "version": "PBK_ENVIRONMENTAL_POSTMATCH_RESEARCH_V1",
        "run_at_utc": iso(captured_at),
        "status": "OK",
        "mode": "POSTMATCH_RESEARCH_ONLY",
        "eligible_unseen_fixtures": len(eligible),
        "selected_fixtures": len(selected),
        "snapshots_total": len(read_csv(SNAPSHOTS)),
        "mechanism_dataset_rows": len(dataset),
        "source_class_counts": dict(sorted(source_counts.items())),
        "mechanism_coverage_counts": dict(sorted(coverage_counts.items())),
        "diagnostics": dict(sorted(diagnostics.items())),
        "source_semantics": {
            "direct_stadium_observation": False,
            "implemented_source_class": config["source_policy"]["implemented_weather_source_class"],
            "usable_for_prematch": False,
            "historical_proxy_is_prematch_forecast": False,
            "geocode_resolver_version": GEOCODE_RESOLVER_VERSION,
            "geocode_country_filter_required": True,
            "geocode_exact_or_token_containment_name_match_required": True,
            "legacy_geocode_rows_are_not_trusted_for_new_captures": True,
        },
        "research_guards": {
            "causal_claim_from_single_match": False,
            "goalkeeper_error_direct_evidence_available": False,
            "unknown_not_zero": True,
            "predictive_authority": "NOT_AUTHORIZED",
            "operational_betting_authority": False,
        },
        "next_stage": (
            "Accumulate postmatch condition snapshots and compare mechanism distributions "
            "across environmental exposures; validate any useful hypothesis separately "
            "against PREMATCH_FROZEN prospective evidence from Stage272."
        ),
    }
    write_json_atomic(META, meta)
    print(json.dumps(meta, ensure_ascii=False))
    return meta


if __name__ == "__main__":
    run()
