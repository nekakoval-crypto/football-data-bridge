"""Capture provider-defined current rounds for the tracked league catalog."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError
from stage72_build_data_layer import today_status

OPS = Path(os.getenv("OPS_DIR", "ops"))
CATALOG = OPS / "stage71_league_catalog.csv"
LEAGUES_OUT = OPS / "current_round_leagues.csv"
FIXTURES_OUT = OPS / "current_round_fixtures.csv"
META_OUT = OPS / "current_round_last_run.json"
SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))

LEAGUE_FIELDS = [
    "provider_league_id", "league_name", "country", "country_flag_url",
    "league_logo_url", "season", "round", "observed_at_utc", "status",
    "error",
]
FIXTURE_FIELDS = [
    "fixture_id", "provider_league_id", "league_name", "country",
    "country_flag_url", "league_logo_url", "season", "round", "kickoff_utc",
    "home_team", "home_team_logo_url", "away_team", "away_team_logo_url",
    "referee", "venue_name", "venue_city",
    "status", "source_status", "score_home", "score_away", "observed_at_utc",
]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def provider_round(payload):
    rounds = (payload or {}).get("response") or []
    return str(rounds[0]) if rounds else None


def extract_fixture(item, league, round_name, observed_at):
    fixture = item.get("fixture") or {}
    provider_league = item.get("league") or {}
    teams = item.get("teams") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    goals = item.get("goals") or {}
    venue = fixture.get("venue") or {}
    raw_status = (fixture.get("status") or {}).get("short")
    return {
        "fixture_id": str(fixture.get("id") or ""),
        "provider_league_id": str(provider_league.get("id") or league.get("api_league_id") or ""),
        "league_name": provider_league.get("name") or league.get("api_league_name") or None,
        "country": provider_league.get("country") or league.get("country") or None,
        "country_flag_url": provider_league.get("flag") or None,
        "league_logo_url": provider_league.get("logo") or None,
        "season": provider_league.get("season") or league.get("season") or None,
        "round": provider_league.get("round") or round_name or None,
        "kickoff_utc": fixture.get("date") or None,
        "home_team": home.get("name") or None,
        "home_team_logo_url": home.get("logo") or None,
        "away_team": away.get("name") or None,
        "away_team_logo_url": away.get("logo") or None,
        "referee": fixture.get("referee") or None,
        "venue_name": venue.get("name") or None,
        "venue_city": venue.get("city") or None,
        "status": today_status(raw_status),
        "source_status": raw_status or None,
        "score_home": goals.get("home"),
        "score_away": goals.get("away"),
        "observed_at_utc": observed_at,
    }


def capture_round(league, observed_at, get=s53.api_get):
    lid = str(league.get("api_league_id") or "")
    if not lid:
        raise RuntimeError("missing provider league ID")
    round_payload = get("/fixtures/rounds", {
        "league": lid, "season": league.get("season") or SEASON, "current": "true",
    }, force_refresh=True)
    round_name = provider_round(round_payload)
    if not round_name:
        raise RuntimeError("provider did not return a current round")
    fixtures_payload = get("/fixtures", {
        "league": lid, "season": league.get("season") or SEASON,
        "round": round_name, "timezone": "UTC",
    }, force_refresh=True)
    fixtures = (fixtures_payload or {}).get("response")
    if not isinstance(fixtures, list):
        raise RuntimeError("provider returned no complete round fixture list")
    if not fixtures:
        raise RuntimeError(f"provider returned an empty fixture list for current round {round_name}")
    rows = [extract_fixture(item, league, round_name, observed_at)
            for item in fixtures if (item.get("fixture") or {}).get("id")]
    if any(row["provider_league_id"] != lid for row in rows):
        raise RuntimeError("fixture league identity mismatch")
    if len({row["fixture_id"] for row in rows}) != len(rows):
        raise RuntimeError("duplicate fixture IDs in current round")
    return round_name, rows


def main():
    observed_at = now_iso()
    previous_leagues = {str(row.get("provider_league_id") or ""): row
                        for row in read_csv(LEAGUES_OUT)}
    previous_fixtures = read_csv(FIXTURES_OUT)
    previous_by_league = {}
    for row in previous_fixtures:
        previous_by_league.setdefault(str(row.get("provider_league_id") or ""), []).append(row)
    leagues = []
    fixtures = []
    warnings = []
    refreshed_leagues = []
    preserved_leagues = []
    failed_leagues = []
    budget_exhausted = False
    state_path = OPS / "stage71_observation_state.json"
    state = audit.read(state_path)
    budget = audit.Budget(
        s53.api_get, state, datetime.now(timezone.utc),
        int(os.getenv("STAGE71_MAX_API_CALLS", "60")),
        int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "180")),
        checkpoint=lambda data: audit.save(state_path, data),
    )
    catalog = read_csv(CATALOG)
    for index, league in enumerate(catalog):
        lid = str(league.get("api_league_id") or "")
        previous = previous_leagues.get(lid)
        previous_rows = previous_by_league.get(lid, [])
        base = {
            "provider_league_id": lid or None,
            "league_name": league.get("api_league_name") or league.get("league") or None,
            "country": league.get("country") or None,
            "country_flag_url": None,
            "league_logo_url": None,
            "season": league.get("season") or SEASON,
            "round": None,
            "observed_at_utc": observed_at,
            "status": "unavailable",
            "error": None,
        }
        try:
            round_name, rows = capture_round(league, observed_at, budget)
            base.update({
                "round": round_name,
                "status": "available",
                "country_flag_url": next((r["country_flag_url"] for r in rows if r["country_flag_url"]), None),
                "league_logo_url": next((r["league_logo_url"] for r in rows if r["league_logo_url"]), None),
            })
            fixtures.extend(rows)
            refreshed_leagues.append(lid)
            leagues.append(base)
        except (ApiFootballBrokerError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            message = str(exc)
            warnings.append(f"{base['league_name']}: {message}")
            failed_leagues.append(lid)
            if previous and previous.get("status") == "available":
                leagues.append(dict(previous))
                fixtures.extend(previous_rows)
                preserved_leagues.append(lid)
            else:
                base["error"] = message
                leagues.append(base)
            if "budget exhausted" in message.lower():
                budget_exhausted = True
                for remaining in catalog[index + 1:]:
                    remaining_id = str(remaining.get("api_league_id") or "")
                    old = previous_leagues.get(remaining_id)
                    old_rows = previous_by_league.get(remaining_id, [])
                    if old and old.get("status") == "available":
                        leagues.append(dict(old))
                        fixtures.extend(old_rows)
                        preserved_leagues.append(remaining_id)
                    else:
                        leagues.append({
                            "provider_league_id": remaining_id or None,
                            "league_name": remaining.get("api_league_name") or remaining.get("league") or None,
                            "country": remaining.get("country") or None,
                            "country_flag_url": None, "league_logo_url": None,
                            "season": remaining.get("season") or SEASON,
                            "round": None, "observed_at_utc": observed_at,
                            "status": "unavailable",
                            "error": message,
                        })
                    failed_leagues.append(remaining_id)
                break
    audit.save(state_path, state)
    fixtures.sort(key=lambda row: (row.get("provider_league_id") or "", row.get("kickoff_utc") or "", row["fixture_id"]))
    write_csv(LEAGUES_OUT, LEAGUE_FIELDS, leagues)
    write_csv(FIXTURES_OUT, FIXTURE_FIELDS, fixtures)
    meta = {
        "run_at_utc": observed_at,
        "status": "ATTENTION" if warnings else "OK",
        "season": SEASON,
        "leagues": len(leagues),
        "available_leagues": sum(row["status"] == "available" for row in leagues),
        "fixture_rows": len(fixtures),
        "warnings": warnings,
        "api_calls": budget.calls,
        "api_day_calls": state.get("api_day_calls", 0),
        "api_budget_limit": budget.limit,
        "api_daily_budget_limit": budget.daily_limit,
        "provider_polling": True,
        "refresh_status": "BUDGET_EXHAUSTED" if budget_exhausted else "PARTIAL" if warnings else "OK",
        "budget_exhausted": budget_exhausted,
        "refreshed_leagues": len(refreshed_leagues),
        "preserved_leagues": len(preserved_leagues),
        "failed_leagues": len(failed_leagues),
        "served_available_leagues": sum(row["status"] == "available" for row in leagues),
        "served_fixture_rows": len(fixtures),
        "last_good_preserved": bool(preserved_leagues),
    }
    META_OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
