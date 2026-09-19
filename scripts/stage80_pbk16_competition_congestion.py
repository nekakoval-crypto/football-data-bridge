#!/usr/bin/env python3
"""Stage80 — PBK16 all-competition historical archive + prior congestion research.

Scope:
- the 16 locked PBK national leagues from ops/stage71_league_catalog.csv;
- selected domestic cups for those countries;
- UEFA Champions League / Europa League / Conference League;
- previous nine completed seasons: 2017..2025.

Collection:
- competition discovery through API-Football /leagues;
- fixture history through /fixtures?league=<id>&season=<year>;
- shared API-Football broker, raw archive and Stage71 daily budget;
- provider-declared unavailable historical seasons are explicit, never fabricated;
- all fixtures from selected competitions are retained. PBK16 club filtering happens
  only in the deterministic projection by provider team_id.

Projection:
- one row per PBK16 domestic-league fixture in the captured archive;
- only strictly earlier played non-league fixtures (FT/AET/PEN) can affect context;
- no future schedule is used in V1;
- research only; no PBK probability, EV/value, R1/R2/R3, stake or Forward authority.
"""
from __future__ import annotations

import bisect
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError, api_get, get_broker

OPS = Path(os.getenv("OPS_DIR", "ops"))
CONFIG = Path("config/stage80_api_football_pbk16_all_competitions_9seasons.json")
LEAGUE_CATALOG = OPS / "stage71_league_catalog.csv"

COMPETITION_CATALOG = OPS / "stage80_pbk16_competition_catalog.csv"
ARCHIVE = OPS / "pbk16_all_competition_fixture_history.csv"
QUERY_STATE = OPS / "stage80_pbk16_competition_backfill_state.csv"
META = OPS / "stage80_pbk16_competition_backfill_last_run.json"
CONGESTION = OPS / "pbk16_competition_congestion_research.csv"
CONGESTION_META = OPS / "stage80_pbk16_competition_congestion_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

VERSION = "PBK_STAGE80_PBK16_ALL_COMPETITION_BACKFILL_V1"
CONGESTION_VERSION = "PBK_STAGE80_PBK16_COMPETITION_CONGESTION_V1"
FINAL = {"FT", "AET", "PEN"}
TERMINAL_STATE = {"CAPTURED", "UNAVAILABLE_PROVIDER_SEASON"}

CATALOG_FIELDS = [
    "competition_role", "country", "slot", "canonical_name",
    "provider_league_id", "provider_name", "provider_type",
    "requested_seasons", "available_requested_seasons", "missing_requested_seasons",
    "required", "discovery_status", "error",
]
ARCHIVE_FIELDS = [
    "fixture_id", "competition_role", "country", "slot",
    "provider_competition_id", "competition_name", "provider_competition_type",
    "season", "round", "kickoff_utc", "status",
    "venue_id", "venue_name", "venue_city",
    "home_team_id", "home_team", "away_team_id", "away_team",
    "home_goals", "away_goals", "result",
    "captured_at_utc", "source",
    "historical_backfill_only", "research_only",
    "operational_betting_authority", "creates_signal", "probability_mutation",
    "eligibility_mutation", "stake_changes", "forward_journal_mutation",
]
STATE_FIELDS = [
    "competition_role", "country", "slot", "provider_competition_id",
    "competition_name", "season", "provider_season_available",
    "status", "attempt_count", "last_attempt_at_utc",
    "provider_fixture_rows", "error",
]
SIDE_FIELDS = [
    "prev_nonleague_fixture_id", "prev_nonleague_competition_id",
    "prev_nonleague_competition_name", "prev_nonleague_competition_role",
    "prev_nonleague_round", "prev_nonleague_kickoff_utc",
    "hours_since_prev_nonleague", "days_since_prev_nonleague",
    "prev_nonleague_weekday_iso", "prev_nonleague_weekday_name_utc",
    "prev_nonleague_was_thursday", "prev_nonleague_was_uefa",
    "prev_nonleague_was_domestic_cup", "prev_nonleague_team_result",
    "nonleague_matches_prev_7d", "nonleague_matches_prev_14d",
    "uefa_matches_prev_7d", "domestic_cup_matches_prev_7d",
]
CONGESTION_FIELDS = [
    "domestic_fixture_id", "provider_league_id", "league_name", "country",
    "season", "round", "kickoff_utc", "status",
    "home_team_id", "home_team", "away_team_id", "away_team",
] + ["home_" + x for x in SIDE_FIELDS] + ["away_" + x for x in SIDE_FIELDS] + [
    "either_team_prev_nonleague_within_72h", "either_team_prev_nonleague_within_96h",
    "either_team_prev_uefa_within_72h", "either_team_prev_uefa_within_96h",
    "either_team_prev_domestic_cup_within_72h",
    "either_team_prev_domestic_cup_within_96h",
    "either_team_previous_nonleague_was_thursday",
    "strictly_prior_fixture_evidence_only", "future_schedule_used", "no_lookahead",
    "historical_backfill_only", "research_only", "operational_betting_authority",
    "creates_signal", "probability_mutation", "eligibility_mutation",
    "stake_changes", "forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def as_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def bool_text(value):
    return "true" if value else "false"


def compact_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def encode_seasons(values):
    return "|".join(str(int(x)) for x in sorted({int(v) for v in values for x in [v]}))


def decode_seasons(value):
    out = []
    for part in str(value or "").split("|"):
        part = part.strip()
        if part:
            out.append(int(part))
    return out


def payload_response(payload):
    if not isinstance(payload, dict):
        raise ValueError("provider payload must be an object")
    errors = payload.get("errors")
    if errors:
        raise RuntimeError(f"provider errors: {errors}")
    paging = payload.get("paging") or {}
    total = as_int(paging.get("total"))
    if total is not None and total > 1:
        raise RuntimeError(f"provider response is paginated (paging.total={total}); explicit paging required")
    rows = payload.get("response")
    if rows is None:
        raise RuntimeError("provider payload has no response")
    if not isinstance(rows, list):
        raise RuntimeError("provider response is not a list")
    return rows


def load_config(path=CONFIG):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    seasons = [int(x) for x in cfg.get("historical_seasons") or []]
    if len(seasons) != 9 or seasons != list(range(2017, 2026)):
        raise ValueError("historical_seasons must be exactly 2017..2025")
    if int(cfg.get("required_league_count") or 0) != 16:
        raise ValueError("required_league_count must be 16")
    return cfg


def load_locked_leagues(cfg, path=LEAGUE_CATALOG):
    rows = read_csv(path)
    rows = [r for r in rows if str(r.get("resolved") or "").upper() == "YES"]
    if len(rows) != int(cfg["required_league_count"]):
        raise RuntimeError(
            f"stage71 league catalog must contain exactly {cfg['required_league_count']} resolved leagues"
        )
    ids = [str(r.get("api_league_id") or "").strip() for r in rows]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise RuntimeError("stage71 league catalog has missing/duplicate provider league IDs")
    countries = [str(r.get("country") or "").strip() for r in rows]
    if any(not x for x in countries) or len(countries) != len(set(countries)):
        raise RuntimeError("stage71 league catalog must have 16 unique countries")
    return rows


def provider_seasons(entry):
    out = set()
    for item in entry.get("seasons") or []:
        year = as_int((item or {}).get("year"))
        if year is not None:
            out.add(year)
    return out


def find_by_id(entries, provider_id):
    matches = []
    for entry in entries:
        league = entry.get("league") or {}
        if as_int(league.get("id")) == int(provider_id):
            matches.append(entry)
    return matches


def find_by_alias(entries, aliases):
    alias_set = {compact_name(x) for x in aliases}
    matches = []
    for entry in entries:
        league = entry.get("league") or {}
        if compact_name(league.get("name")) in alias_set:
            matches.append(entry)
    return matches


def catalog_row(role, country, slot, canonical, requested, required, entry=None, error=""):
    requested = [int(x) for x in requested]
    if entry:
        league = entry.get("league") or {}
        available = sorted(set(requested) & provider_seasons(entry))
        missing = sorted(set(requested) - set(available))
        return {
            "competition_role": role,
            "country": country,
            "slot": slot,
            "canonical_name": canonical,
            "provider_league_id": str(league.get("id") or ""),
            "provider_name": str(league.get("name") or ""),
            "provider_type": str(league.get("type") or ""),
            "requested_seasons": encode_seasons(requested),
            "available_requested_seasons": encode_seasons(available),
            "missing_requested_seasons": encode_seasons(missing),
            "required": bool_text(required),
            "discovery_status": "RESOLVED",
            "error": "",
        }
    return {
        "competition_role": role,
        "country": country,
        "slot": slot,
        "canonical_name": canonical,
        "provider_league_id": "",
        "provider_name": "",
        "provider_type": "",
        "requested_seasons": encode_seasons(requested),
        "available_requested_seasons": "",
        "missing_requested_seasons": encode_seasons(requested),
        "required": bool_text(required),
        "discovery_status": "UNRESOLVED",
        "error": error or "competition not resolved",
    }


def protected_calls():
    return max(0, int(os.getenv("STAGE80_PBK16_COMPETITION_PROTECTED_CALLS", "512")))


def discover_catalog(cfg, locked_leagues, budget):
    seasons = [int(x) for x in cfg["historical_seasons"]]
    cup_by_country = defaultdict(list)
    for slot in cfg.get("domestic_cup_slots") or []:
        cup_by_country[str(slot["country"])].append(slot)

    catalog = []
    warnings = []
    country_payloads = {}

    for league in locked_leagues:
        country = str(league["country"])
        try:
            payload = budget(
                cfg.get("discovery_endpoint") or "/leagues",
                {"country": country},
                ttl_seconds=365 * 24 * 3600,
                force_refresh=False,
            )
            entries = payload_response(payload)
            country_payloads[country] = entries
        except (ApiFootballBrokerError, audit.ProtectedBudgetError, RuntimeError, ValueError) as exc:
            country_payloads[country] = []
            warnings.append(f"discovery:{country}: {exc}")

    for league in locked_leagues:
        country = str(league["country"])
        entries = country_payloads.get(country, [])
        provider_id = int(league["api_league_id"])
        matches = find_by_id(entries, provider_id)
        if len(matches) == 1:
            catalog.append(catalog_row(
                "DOMESTIC_LEAGUE", country, "LEAGUE",
                str(league.get("league") or league.get("api_league_name") or ""),
                seasons, True, entry=matches[0],
            ))
        else:
            err = f"expected provider league id {provider_id}; matches={len(matches)}"
            catalog.append(catalog_row(
                "DOMESTIC_LEAGUE", country, "LEAGUE",
                str(league.get("league") or league.get("api_league_name") or ""),
                seasons, True, error=err,
            ))
            warnings.append(f"discovery:{country}: {err}")

        for slot in cup_by_country.get(country, []):
            requested = [int(x) for x in slot.get("seasons") or seasons]
            matches = find_by_alias(entries, slot.get("provider_name_aliases") or [])
            matches = [
                x for x in matches
                if compact_name((x.get("league") or {}).get("type")) == "cup"
            ]
            if len(matches) == 1:
                catalog.append(catalog_row(
                    "DOMESTIC_CUP", country, str(slot["slot"]),
                    str(slot["canonical_name"]), requested,
                    bool(slot.get("required", True)), entry=matches[0],
                ))
            else:
                err = (
                    f"cup alias resolution failed for {slot['canonical_name']}; "
                    f"matches={len(matches)}"
                )
                catalog.append(catalog_row(
                    "DOMESTIC_CUP", country, str(slot["slot"]),
                    str(slot["canonical_name"]), requested,
                    bool(slot.get("required", True)), error=err,
                ))
                if slot.get("required", True):
                    warnings.append(f"discovery:{country}: {err}")

    for comp in cfg.get("uefa_competitions") or []:
        provider_id = int(comp["provider_league_id"])
        try:
            payload = budget(
                cfg.get("discovery_endpoint") or "/leagues",
                {"id": provider_id},
                ttl_seconds=365 * 24 * 3600,
                force_refresh=False,
            )
            entries = payload_response(payload)
        except (ApiFootballBrokerError, audit.ProtectedBudgetError, RuntimeError, ValueError) as exc:
            entries = []
            warnings.append(f"discovery:UEFA:{provider_id}: {exc}")

        matches = find_by_id(entries, provider_id)
        aliases = {compact_name(x) for x in comp.get("provider_name_aliases") or []}
        matches = [
            x for x in matches
            if not aliases or compact_name((x.get("league") or {}).get("name")) in aliases
        ]
        requested = [int(x) for x in comp.get("seasons") or seasons]
        if len(matches) == 1:
            catalog.append(catalog_row(
                "UEFA", "International", str(comp["slot"]),
                str(comp["canonical_name"]), requested,
                bool(comp.get("required", True)), entry=matches[0],
            ))
        else:
            err = f"UEFA provider id {provider_id} resolution failed; matches={len(matches)}"
            catalog.append(catalog_row(
                "UEFA", "International", str(comp["slot"]),
                str(comp["canonical_name"]), requested,
                bool(comp.get("required", True)), error=err,
            ))
            if comp.get("required", True):
                warnings.append(f"discovery:UEFA:{provider_id}: {err}")

    catalog.sort(key=lambda r: (
        {"DOMESTIC_LEAGUE": 0, "DOMESTIC_CUP": 1, "UEFA": 2}.get(r["competition_role"], 9),
        r["country"], r["slot"], r["canonical_name"],
    ))
    return catalog, warnings


def query_key(row):
    return (
        str(row.get("provider_competition_id") or ""),
        str(row.get("season") or ""),
    )


def build_query_specs(catalog):
    specs = []
    for comp in catalog:
        if comp.get("discovery_status") != "RESOLVED":
            continue
        available = set(decode_seasons(comp.get("available_requested_seasons")))
        for season in decode_seasons(comp.get("requested_seasons")):
            specs.append({
                "competition_role": comp["competition_role"],
                "country": comp["country"],
                "slot": comp["slot"],
                "provider_competition_id": int(comp["provider_league_id"]),
                "competition_name": comp["provider_name"] or comp["canonical_name"],
                "season": int(season),
                "provider_season_available": season in available,
            })
    specs.sort(key=lambda r: (
        0 if r["competition_role"] == "DOMESTIC_LEAGUE" else 1,
        r["country"], r["provider_competition_id"], r["season"],
    ))
    return specs


def state_rows_for_specs(specs, existing):
    by = {query_key(r): dict(r) for r in existing if all(query_key(r))}
    rows = []
    for spec in specs:
        key = (str(spec["provider_competition_id"]), str(spec["season"]))
        row = by.get(key, {field: "" for field in STATE_FIELDS})
        row.update({
            "competition_role": spec["competition_role"],
            "country": spec["country"],
            "slot": spec["slot"],
            "provider_competition_id": key[0],
            "competition_name": spec["competition_name"],
            "season": key[1],
            "provider_season_available": bool_text(spec["provider_season_available"]),
        })
        if not spec["provider_season_available"]:
            row["status"] = "UNAVAILABLE_PROVIDER_SEASON"
            row["provider_fixture_rows"] = ""
            row["error"] = ""
        elif row.get("status") == "UNAVAILABLE_PROVIDER_SEASON":
            row["status"] = "PENDING"
        elif not row.get("status"):
            row["status"] = "PENDING"
        if not row.get("attempt_count"):
            row["attempt_count"] = "0"
        rows.append(row)
    return rows


def result_code(status, home, away):
    if status not in FINAL or home is None or away is None:
        return ""
    if home > away:
        return "H"
    if home < away:
        return "A"
    return "D"


def normalize_fixture_payload(payload, spec, captured_at):
    response = payload_response(payload)
    rows = []
    for item in response:
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        if as_int(league.get("id")) != int(spec["provider_competition_id"]):
            raise RuntimeError(
                f"fixture league identity mismatch: expected {spec['provider_competition_id']}, "
                f"got {league.get('id')}"
            )
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        fid = str(fixture.get("id") or "").strip()
        hid = str(home.get("id") or "").strip()
        aid = str(away.get("id") or "").strip()
        if not (fid and hid and aid):
            continue
        status = str((fixture.get("status") or {}).get("short") or "").strip()
        venue = fixture.get("venue") or {}
        hg = as_int(goals.get("home"))
        ag = as_int(goals.get("away"))
        rows.append({
            "fixture_id": fid,
            "competition_role": spec["competition_role"],
            "country": str(league.get("country") or spec["country"]),
            "slot": spec["slot"],
            "provider_competition_id": str(league.get("id") or spec["provider_competition_id"]),
            "competition_name": str(league.get("name") or spec["competition_name"]),
            "provider_competition_type": str(league.get("type") or ""),
            "season": str(league.get("season") or spec["season"]),
            "round": str(league.get("round") or ""),
            "kickoff_utc": str(fixture.get("date") or ""),
            "status": status,
            "venue_id": str(venue.get("id") or ""),
            "venue_name": str(venue.get("name") or ""),
            "venue_city": str(venue.get("city") or ""),
            "home_team_id": hid,
            "home_team": str(home.get("name") or ""),
            "away_team_id": aid,
            "away_team": str(away.get("name") or ""),
            "home_goals": "" if hg is None else hg,
            "away_goals": "" if ag is None else ag,
            "result": result_code(status, hg, ag),
            "captured_at_utc": captured_at,
            "source": "API-Football /fixtures?league&season",
            "historical_backfill_only": "true",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })
    return len(response), rows


def archive_key(row):
    return str(row.get("fixture_id") or "").strip()


def merge_archive(existing, incoming):
    merged = {archive_key(r): dict(r) for r in existing if archive_key(r)}
    for row in incoming:
        key = archive_key(row)
        if key:
            merged[key] = dict(row)
    return sorted(
        merged.values(),
        key=lambda r: (
            str(r.get("kickoff_utc") or ""),
            str(r.get("fixture_id") or ""),
        ),
    )


def team_result(row, team_id):
    result = str(row.get("result") or "")
    if result not in {"H", "D", "A"}:
        return ""
    if result == "D":
        return "D"
    hid = str(row.get("home_team_id") or "")
    aid = str(row.get("away_team_id") or "")
    if team_id not in {hid, aid}:
        return ""
    if (result == "H" and team_id == hid) or (result == "A" and team_id == aid):
        return "W"
    return "L"


def build_played_nonleague_index(archive_rows):
    by = defaultdict(list)
    for row in archive_rows:
        if str(row.get("competition_role") or "") == "DOMESTIC_LEAGUE":
            continue
        if str(row.get("status") or "") not in FINAL:
            continue
        kickoff = parse_dt(row.get("kickoff_utc"))
        season = str(row.get("season") or "").strip()
        if not kickoff or not season:
            continue
        for key in ("home_team_id", "away_team_id"):
            tid = str(row.get(key) or "").strip()
            if tid:
                by[(season, tid)].append((kickoff, row))
    for key in by:
        by[key].sort(key=lambda item: (
            item[0], str(item[1].get("fixture_id") or "")
        ))
    return by


def side_context(team_id, season, kickoff, index):
    items = index.get((season, team_id), [])
    times = [item[0] for item in items]
    pos = bisect.bisect_left(times, kickoff)
    prior = items[:pos]
    prev = prior[-1] if prior else None
    out = {field: "" for field in SIDE_FIELDS}
    if prev:
        prev_dt, row = prev
        hours = (kickoff - prev_dt).total_seconds() / 3600.0
        role = str(row.get("competition_role") or "")
        out.update({
            "prev_nonleague_fixture_id": str(row.get("fixture_id") or ""),
            "prev_nonleague_competition_id": str(row.get("provider_competition_id") or ""),
            "prev_nonleague_competition_name": str(row.get("competition_name") or ""),
            "prev_nonleague_competition_role": role,
            "prev_nonleague_round": str(row.get("round") or ""),
            "prev_nonleague_kickoff_utc": str(row.get("kickoff_utc") or ""),
            "hours_since_prev_nonleague": round(hours, 3),
            "days_since_prev_nonleague": round(hours / 24.0, 3),
            "prev_nonleague_weekday_iso": prev_dt.isoweekday(),
            "prev_nonleague_weekday_name_utc": prev_dt.strftime("%A").upper(),
            "prev_nonleague_was_thursday": bool_text(prev_dt.isoweekday() == 4),
            "prev_nonleague_was_uefa": bool_text(role == "UEFA"),
            "prev_nonleague_was_domestic_cup": bool_text(role == "DOMESTIC_CUP"),
            "prev_nonleague_team_result": team_result(row, team_id),
        })

    prev7 = [
        item for item in prior
        if 0 < (kickoff - item[0]).total_seconds() <= 7 * 86400
    ]
    prev14 = [
        item for item in prior
        if 0 < (kickoff - item[0]).total_seconds() <= 14 * 86400
    ]
    out["nonleague_matches_prev_7d"] = len(prev7)
    out["nonleague_matches_prev_14d"] = len(prev14)
    out["uefa_matches_prev_7d"] = sum(
        str(item[1].get("competition_role") or "") == "UEFA" for item in prev7
    )
    out["domestic_cup_matches_prev_7d"] = sum(
        str(item[1].get("competition_role") or "") == "DOMESTIC_CUP"
        for item in prev7
    )
    return out


def within_hours(side, kind, hours):
    try:
        value = float(side.get("hours_since_prev_nonleague"))
    except (TypeError, ValueError):
        return False
    if not (0 < value <= hours):
        return False
    if kind == "ANY":
        return True
    if kind == "UEFA":
        return side.get("prev_nonleague_was_uefa") == "true"
    if kind == "DOMESTIC_CUP":
        return side.get("prev_nonleague_was_domestic_cup") == "true"
    return False


def build_congestion(archive_rows):
    domestic_rows = [
        row for row in archive_rows
        if str(row.get("competition_role") or "") == "DOMESTIC_LEAGUE"
    ]
    index = build_played_nonleague_index(archive_rows)
    out = []
    invalid_domestic = 0

    for row in domestic_rows:
        kickoff = parse_dt(row.get("kickoff_utc"))
        season = str(row.get("season") or "").strip()
        hid = str(row.get("home_team_id") or "").strip()
        aid = str(row.get("away_team_id") or "").strip()
        fid = str(row.get("fixture_id") or "").strip()
        if not (kickoff and season and hid and aid and fid):
            invalid_domestic += 1
            continue

        home = side_context(hid, season, kickoff, index)
        away = side_context(aid, season, kickoff, index)
        record = {
            "domestic_fixture_id": fid,
            "provider_league_id": str(row.get("provider_competition_id") or ""),
            "league_name": str(row.get("competition_name") or ""),
            "country": str(row.get("country") or ""),
            "season": season,
            "round": str(row.get("round") or ""),
            "kickoff_utc": str(row.get("kickoff_utc") or ""),
            "status": str(row.get("status") or ""),
            "home_team_id": hid,
            "home_team": str(row.get("home_team") or ""),
            "away_team_id": aid,
            "away_team": str(row.get("away_team") or ""),
        }
        record.update({"home_" + key: value for key, value in home.items()})
        record.update({"away_" + key: value for key, value in away.items()})
        record.update({
            "either_team_prev_nonleague_within_72h": bool_text(
                within_hours(home, "ANY", 72) or within_hours(away, "ANY", 72)
            ),
            "either_team_prev_nonleague_within_96h": bool_text(
                within_hours(home, "ANY", 96) or within_hours(away, "ANY", 96)
            ),
            "either_team_prev_uefa_within_72h": bool_text(
                within_hours(home, "UEFA", 72) or within_hours(away, "UEFA", 72)
            ),
            "either_team_prev_uefa_within_96h": bool_text(
                within_hours(home, "UEFA", 96) or within_hours(away, "UEFA", 96)
            ),
            "either_team_prev_domestic_cup_within_72h": bool_text(
                within_hours(home, "DOMESTIC_CUP", 72)
                or within_hours(away, "DOMESTIC_CUP", 72)
            ),
            "either_team_prev_domestic_cup_within_96h": bool_text(
                within_hours(home, "DOMESTIC_CUP", 96)
                or within_hours(away, "DOMESTIC_CUP", 96)
            ),
            "either_team_previous_nonleague_was_thursday": bool_text(
                home.get("prev_nonleague_was_thursday") == "true"
                or away.get("prev_nonleague_was_thursday") == "true"
            ),
            "strictly_prior_fixture_evidence_only": "true",
            "future_schedule_used": "false",
            "no_lookahead": "true",
            "historical_backfill_only": "true",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })
        out.append(record)

    out.sort(key=lambda r: (r["kickoff_utc"], r["domestic_fixture_id"]))
    return domestic_rows, out, invalid_domestic


def run(config_path=CONFIG, get=api_get, now=None):
    now = now or datetime.now(timezone.utc)
    cfg = load_config(config_path)
    locked_leagues = load_locked_leagues(cfg)

    shared = audit.read(SHARED_STATE)
    budget = audit.Budget(
        get,
        shared,
        now,
        limit=int(os.getenv("STAGE80_PBK16_COMPETITION_MAX_API_CALLS", "512")),
        daily_limit=int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "7000")),
        checkpoint=lambda state: audit.save(SHARED_STATE, state),
        protected_calls=protected_calls(),
    )
    calls_before = int(shared.get("api_day_calls") or 0)

    catalog, discovery_warnings = discover_catalog(cfg, locked_leagues, budget)
    write_csv(COMPETITION_CATALOG, CATALOG_FIELDS, catalog)

    specs = build_query_specs(catalog)
    state = state_rows_for_specs(specs, read_csv(QUERY_STATE))
    archive = read_csv(ARCHIVE)
    warnings = list(discovery_warnings)

    for row, spec in zip(state, specs):
        if row.get("status") in TERMINAL_STATE:
            continue
        attempted = iso_now()
        try:
            payload = budget(
                cfg.get("fixture_endpoint") or "/fixtures",
                {
                    "league": spec["provider_competition_id"],
                    "season": spec["season"],
                },
                ttl_seconds=365 * 24 * 3600,
                force_refresh=False,
            )
            provider_rows, normalized = normalize_fixture_payload(payload, spec, attempted)
            if provider_rows <= 0:
                raise RuntimeError("provider returned zero fixtures for a declared available season")
            archive = merge_archive(archive, normalized)
            row["status"] = "CAPTURED"
            row["provider_fixture_rows"] = str(provider_rows)
            row["error"] = ""
        except audit.ProtectedBudgetError as exc:
            warnings.append(str(exc))
            break
        except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            row["status"] = "ERROR"
            row["error"] = str(exc)
            warnings.append(
                f"{spec['provider_competition_id']}:{spec['season']}: {exc}"
            )
        finally:
            if row.get("last_attempt_at_utc") != attempted:
                try:
                    row["attempt_count"] = str(int(row.get("attempt_count") or 0) + 1)
                except ValueError:
                    row["attempt_count"] = "1"
                row["last_attempt_at_utc"] = attempted
            write_csv(ARCHIVE, ARCHIVE_FIELDS, archive)
            write_csv(QUERY_STATE, STATE_FIELDS, state)

    domestic_rows, congestion, invalid_domestic = build_congestion(archive)
    write_csv(CONGESTION, CONGESTION_FIELDS, congestion)
    audit.save(SHARED_STATE, shared)

    required_unresolved = sum(
        row.get("discovery_status") != "RESOLVED" and row.get("required") == "true"
        for row in catalog
    )
    optional_unresolved = sum(
        row.get("discovery_status") != "RESOLVED" and row.get("required") != "true"
        for row in catalog
    )
    captured = sum(row.get("status") == "CAPTURED" for row in state)
    unavailable = sum(row.get("status") == "UNAVAILABLE_PROVIDER_SEASON" for row in state)
    errors = sum(row.get("status") == "ERROR" for row in state)
    pending = sum(row.get("status") == "PENDING" for row in state)

    role_archive_counts = {
        role: sum(str(row.get("competition_role") or "") == role for row in archive)
        for role in ("DOMESTIC_LEAGUE", "DOMESTIC_CUP", "UEFA")
    }
    role_catalog_counts = {
        role: sum(
            row.get("competition_role") == role
            and row.get("discovery_status") == "RESOLVED"
            for row in catalog
        )
        for role in ("DOMESTIC_LEAGUE", "DOMESTIC_CUP", "UEFA")
    }
    domestic_league_ids = {
        str(row.get("provider_competition_id") or "")
        for row in domestic_rows
        if row.get("provider_competition_id")
    }
    broker_stats = get_broker().stats() if get is api_get else {}

    if required_unresolved or errors or pending:
        status = "ATTENTION"
    elif unavailable or optional_unresolved:
        status = "PARTIAL_PROVIDER_COVERAGE"
    else:
        status = "OK"

    meta = {
        "version": VERSION,
        "run_at_utc": iso_now(),
        "status": status,
        "locked_national_leagues": len(locked_leagues),
        "resolved_competitions": sum(
            row.get("discovery_status") == "RESOLVED" for row in catalog
        ),
        "resolved_competitions_by_role": role_catalog_counts,
        "required_unresolved_competitions": required_unresolved,
        "optional_unresolved_competitions": optional_unresolved,
        "requested_fixture_cells": len(state),
        "captured_fixture_cells": captured,
        "unavailable_provider_season_cells": unavailable,
        "pending_fixture_cells": pending,
        "error_fixture_cells": errors,
        "archive_rows": len(archive),
        "archive_rows_by_role": role_archive_counts,
        "domestic_anchor_rows": len(domestic_rows),
        "domestic_anchor_league_ids": len(domestic_league_ids),
        "congestion_rows": len(congestion),
        "invalid_domestic_anchor_rows": invalid_domestic,
        "provider_budget_calls": budget.calls,
        "real_api_calls": broker_stats.get("real_api_calls"),
        "daily_api_calls_before": calls_before,
        "daily_api_calls_after": int(shared.get("api_day_calls") or 0),
        "protected_calls": protected_calls(),
        "warnings": warnings,
        "historical_backfill_only": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    write_json(META, meta)

    congestion_meta = {
        "version": CONGESTION_VERSION,
        "run_at_utc": iso_now(),
        "status": (
            "OK"
            if invalid_domestic == 0 and len(congestion) == len(domestic_rows)
            else "ATTENTION"
        ),
        "source_archive_rows": len(archive),
        "source_domestic_rows": len(domestic_rows),
        "source_nonleague_rows": (
            len(archive) - len(domestic_rows)
        ),
        "output_rows": len(congestion),
        "unique_domestic_fixture_ids": len({
            row["domestic_fixture_id"] for row in congestion
        }),
        "domestic_anchor_league_ids": len(domestic_league_ids),
        "invalid_domestic_anchor_rows": invalid_domestic,
        "rows_with_home_prior_nonleague": sum(
            bool(row.get("home_prev_nonleague_fixture_id")) for row in congestion
        ),
        "rows_with_away_prior_nonleague": sum(
            bool(row.get("away_prev_nonleague_fixture_id")) for row in congestion
        ),
        "rows_either_prev_nonleague_72h": sum(
            row["either_team_prev_nonleague_within_72h"] == "true"
            for row in congestion
        ),
        "rows_either_prev_nonleague_96h": sum(
            row["either_team_prev_nonleague_within_96h"] == "true"
            for row in congestion
        ),
        "rows_either_prev_uefa_72h": sum(
            row["either_team_prev_uefa_within_72h"] == "true"
            for row in congestion
        ),
        "rows_either_prev_uefa_96h": sum(
            row["either_team_prev_uefa_within_96h"] == "true"
            for row in congestion
        ),
        "rows_either_prev_cup_72h": sum(
            row["either_team_prev_domestic_cup_within_72h"] == "true"
            for row in congestion
        ),
        "rows_either_prev_cup_96h": sum(
            row["either_team_prev_domestic_cup_within_96h"] == "true"
            for row in congestion
        ),
        "rows_either_previous_nonleague_was_thursday": sum(
            row["either_team_previous_nonleague_was_thursday"] == "true"
            for row in congestion
        ),
        "strictly_prior_fixture_evidence_only": True,
        "future_schedule_used": False,
        "no_lookahead": True,
        "projection_provider_calls": 0,
        "historical_backfill_only": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    write_json(CONGESTION_META, congestion_meta)
    return meta, congestion_meta


def main():
    meta, congestion = run()
    print(json.dumps(
        {"backfill": meta, "congestion": congestion},
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
