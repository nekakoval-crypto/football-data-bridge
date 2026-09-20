#!/usr/bin/env python3
"""Stage80 PBK16 historical lineup/injury availability probe.

Purpose
-------
Measure whether API-Football exposes useful historical fixture-scoped evidence
for:
- /fixtures/lineups
- /injuries

The probe is deliberately bounded and research-only. It samples a deterministic
set of terminal domestic-league fixtures across PBK16, queries both endpoints
through the existing shared broker/budget layer, and writes only availability
telemetry. Provider payloads remain in the existing raw archive when the broker
performs real provider calls.

This stage does NOT normalize historical lineups/injuries into model features and
does NOT grant betting/model authority. Historical temporal semantics are not
assumed: a response retrieved today for an old fixture is retrospective evidence
unless a later stage proves a valid pre-match observation time.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import stage53_daily_screener as s53
    import stage71_observation_audit as audit
    import stage77_player_stats_capture as current
    from api_football_broker import ApiFootballBrokerError
except ModuleNotFoundError:
    from scripts import stage53_daily_screener as s53
    from scripts import stage71_observation_audit as audit
    from scripts import stage77_player_stats_capture as current
    from scripts.api_football_broker import ApiFootballBrokerError


OPS = Path(os.getenv("OPS_DIR", "ops"))
SOURCE = OPS / "pbk16_all_competition_fixture_history.csv"
OUT = OPS / "stage80_historical_lineup_injury_probe.csv"
META = OPS / "stage80_historical_lineup_injury_probe_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

VERSION = "PBK_STAGE80_HISTORICAL_LINEUP_INJURY_PROBE_V1"
TERMINAL = {"FT", "AET", "PEN", "FINISHED"}
ENDPOINTS = ("/fixtures/lineups", "/injuries")

FIELDS = [
    "fixture_id",
    "country",
    "provider_competition_id",
    "competition_name",
    "season",
    "round",
    "kickoff_utc",
    "home_team",
    "away_team",
    "endpoint",
    "result",
    "response_rows",
    "attempted_at_utc",
    "error",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv_atomic(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def season_number(row):
    try:
        return int(sval(row, "season"))
    except ValueError:
        return -1


def eligible_domestic_league_rows(rows):
    out = []
    seen = set()
    for row in rows:
        fixture_id = sval(row, "fixture_id")
        status = sval(row, "status").upper()
        role = sval(row, "competition_role").upper()
        country = sval(row, "country")
        if not fixture_id or fixture_id in seen:
            continue
        if status not in TERMINAL:
            continue
        if "LEAGUE" not in role or "UEFA" in role:
            continue
        if not country:
            continue
        seen.add(fixture_id)
        out.append(dict(row))
    return out


def evenly_spaced(rows, count):
    rows = list(rows)
    if count <= 0 or not rows:
        return []
    if len(rows) <= count:
        return rows
    if count == 1:
        return [rows[len(rows) // 2]]

    indexes = []
    for i in range(count):
        idx = round(i * (len(rows) - 1) / (count - 1))
        if idx not in indexes:
            indexes.append(idx)
    return [rows[idx] for idx in indexes]


def deterministic_sample(rows, expected_leagues=16, per_league=8, seasons_per_league=4):
    eligible = eligible_domestic_league_rows(rows)
    by_country = defaultdict(list)
    for row in eligible:
        by_country[sval(row, "country")].append(row)

    countries = sorted(by_country)
    if len(countries) != expected_leagues:
        raise RuntimeError(
            f"Expected {expected_leagues} PBK16 domestic leagues/countries, "
            f"found {len(countries)}: {countries}"
        )

    selected = []
    for country in countries:
        country_rows = by_country[country]
        by_season = defaultdict(list)
        for row in country_rows:
            by_season[sval(row, "season")].append(row)

        seasons = sorted(
            by_season,
            key=lambda value: int(value) if str(value).isdigit() else -1,
            reverse=True,
        )[:seasons_per_league]

        country_selected = []
        selected_ids = set()
        base_per_season = max(1, per_league // max(1, len(seasons)))

        for season in seasons:
            cell = sorted(
                by_season[season],
                key=lambda row: (sval(row, "kickoff_utc"), sval(row, "fixture_id")),
            )
            for row in evenly_spaced(cell, min(base_per_season, len(cell))):
                fid = sval(row, "fixture_id")
                if fid not in selected_ids and len(country_selected) < per_league:
                    selected_ids.add(fid)
                    country_selected.append(row)

        if len(country_selected) < per_league:
            remainder = sorted(
                country_rows,
                key=lambda row: (
                    -season_number(row),
                    sval(row, "kickoff_utc"),
                    sval(row, "fixture_id"),
                ),
            )
            for row in remainder:
                fid = sval(row, "fixture_id")
                if fid in selected_ids:
                    continue
                selected_ids.add(fid)
                country_selected.append(row)
                if len(country_selected) >= per_league:
                    break

        if len(country_selected) != per_league:
            raise RuntimeError(
                f"Country {country} produced {len(country_selected)} sampled fixtures; "
                f"expected {per_league}"
            )

        selected.extend(country_selected)

    return selected


def classify_payload(payload):
    if not isinstance(payload, dict):
        return "ERROR", 0
    response = payload.get("response")
    if not isinstance(response, list):
        return "ERROR", 0
    return ("CAPTURED", len(response)) if response else ("NO_DATA", 0)


def is_provider_quota_error(exc):
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "request limit for the day",
            "http 429",
            "too many requests",
            "rate limit",
        )
    )


def endpoint_summary(rows):
    out = {}
    for endpoint in ENDPOINTS:
        subset = [row for row in rows if row["endpoint"] == endpoint]
        counts = Counter(row["result"] for row in subset)
        out[endpoint] = {
            "attempts": len(subset),
            "captured": counts.get("CAPTURED", 0),
            "no_data": counts.get("NO_DATA", 0),
            "errors": counts.get("ERROR", 0),
            "response_rows": sum(int(row["response_rows"] or 0) for row in subset),
        }
    return out


def cell_summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["country"], row["season"], row["endpoint"])].append(row)

    output = []
    for (country, season, endpoint), subset in sorted(grouped.items()):
        counts = Counter(row["result"] for row in subset)
        output.append(
            {
                "country": country,
                "season": season,
                "endpoint": endpoint,
                "attempts": len(subset),
                "captured": counts.get("CAPTURED", 0),
                "no_data": counts.get("NO_DATA", 0),
                "errors": counts.get("ERROR", 0),
                "response_rows": sum(
                    int(row["response_rows"] or 0)
                    for row in subset
                ),
            }
        )
    return output


def main():
    now = datetime.now(timezone.utc)
    source_rows = read_csv(SOURCE)

    expected_leagues = int(
        os.getenv("STAGE80_HISTORICAL_PROBE_EXPECTED_LEAGUES", "16")
    )
    per_league = int(
        os.getenv("STAGE80_HISTORICAL_PROBE_FIXTURES_PER_LEAGUE", "8")
    )
    seasons_per_league = int(
        os.getenv("STAGE80_HISTORICAL_PROBE_SEASONS_PER_LEAGUE", "4")
    )
    max_calls = int(
        os.getenv("STAGE80_HISTORICAL_PROBE_MAX_API_CALLS", "256")
    )
    daily_limit = int(
        os.getenv("STAGE71_MAX_DAILY_API_CALLS", "7000")
    )

    sample = deterministic_sample(
        source_rows,
        expected_leagues=expected_leagues,
        per_league=per_league,
        seasons_per_league=seasons_per_league,
    )

    required_calls = len(sample) * len(ENDPOINTS)
    if required_calls > max_calls:
        raise RuntimeError(
            f"Probe needs {required_calls} endpoint calls but max_calls={max_calls}"
        )

    shared_state = audit.read(SHARED_STATE)
    reserve = current.protected_calls(OPS, now)
    budget = audit.Budget(
        s53.api_get,
        shared_state,
        now,
        limit=max_calls,
        daily_limit=daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(SHARED_STATE, value),
    )

    output = []
    warnings = []
    quota_exhausted = False
    quota_error = ""

    for fixture in sample:
        fixture_id = sval(fixture, "fixture_id")

        for endpoint in ENDPOINTS:
            attempted_at = iso(now)
            try:
                payload = budget(
                    endpoint,
                    {"fixture": fixture_id},
                    ttl_seconds=30 * 24 * 3600,
                    force_refresh=True,
                )
                result, response_rows = classify_payload(payload)
                error = ""
            except audit.ProtectedBudgetError as exc:
                warnings.append(str(exc))
                quota_exhausted = True
                quota_error = f"{type(exc).__name__}: {exc}"
                break
            except (
                ApiFootballBrokerError,
                RuntimeError,
                ValueError,
                TypeError,
                KeyError,
            ) as exc:
                result = "ERROR"
                response_rows = 0
                error = f"{type(exc).__name__}: {exc}"
                if is_provider_quota_error(exc):
                    quota_exhausted = True
                    quota_error = error

            output.append(
                {
                    "fixture_id": fixture_id,
                    "country": sval(fixture, "country"),
                    "provider_competition_id": sval(
                        fixture, "provider_competition_id"
                    ),
                    "competition_name": sval(fixture, "competition_name"),
                    "season": sval(fixture, "season"),
                    "round": sval(fixture, "round"),
                    "kickoff_utc": sval(fixture, "kickoff_utc"),
                    "home_team": sval(fixture, "home_team"),
                    "away_team": sval(fixture, "away_team"),
                    "endpoint": endpoint,
                    "result": result,
                    "response_rows": str(response_rows),
                    "attempted_at_utc": attempted_at,
                    "error": error,
                }
            )

            if quota_exhausted:
                break

        if quota_exhausted:
            break

    write_csv_atomic(OUT, FIELDS, output)
    audit.save(SHARED_STATE, shared_state)

    countries = sorted({sval(row, "country") for row in sample})
    seasons = sorted(
        {sval(row, "season") for row in sample},
        key=lambda value: int(value) if value.isdigit() else -1,
    )

    meta = {
        "version": VERSION,
        "run_at_utc": iso(now),
        "status": "ATTENTION" if quota_exhausted or any(
            row["result"] == "ERROR" for row in output
        ) else "OK",
        "source_rows": len(source_rows),
        "sampled_fixtures": len(sample),
        "expected_leagues": expected_leagues,
        "sampled_countries": countries,
        "sampled_country_count": len(countries),
        "fixtures_per_league": per_league,
        "seasons_per_league_target": seasons_per_league,
        "sampled_seasons": seasons,
        "endpoint_count": len(ENDPOINTS),
        "planned_endpoint_calls": required_calls,
        "provider_calls": budget.calls,
        "max_provider_calls": max_calls,
        "daily_api_calls": shared_state.get("api_day_calls", 0),
        "protected_calls": reserve,
        "endpoint_summary": endpoint_summary(output),
        "cell_summary": cell_summary(output),
        "provider_quota_exhausted": quota_exhausted,
        "provider_quota_error": quota_error,
        "warnings": warnings,
        "raw_archive_via_shared_broker": True,
        "force_refresh": True,
        "research_only": True,
        "retrospective_reconstructed": True,
        "temporal_authority": "RESEARCH_ONLY_RETROSPECTIVE",
        "pre_match_observation_time_known": False,
        "eligible_for_predictive_validation": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }

    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
