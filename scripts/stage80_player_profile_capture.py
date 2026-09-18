#!/usr/bin/env python3
"""Stage80 — low-priority API-Football player profile enrichment.

Collects /players?team=<id>&season=<season> through the shared broker only.
The collector is identity/research enrichment, not betting authority.

Safety:
- shared Stage71 daily state and protected reserve;
- bounded calls/teams per run;
- complete pagination required before a team is persisted;
- no partial team evidence is written;
- one durable row per team+season+player, updated only by explicit recapture.
"""
from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError

OPS = Path(os.getenv("OPS_DIR", "ops"))
ROSTERS = OPS / "team_rosters.csv"
FIXTURES = OPS / "current_round_fixtures.csv"
OUT = OPS / "player_profile_evidence.csv"
META = OPS / "stage80_player_profile_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

TEAM_ID_RE = re.compile(r"/teams/(\d+)")
FIELDS = [
    "team_id","team_name","season","player_id","player_name","firstname","lastname",
    "birth_date","birth_place","birth_country","nationality","height","weight",
    "injured","photo_url","captured_at_utc","source",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_csv(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def team_id_from_fixture(row, side):
    explicit = str(row.get(f"{side}_team_id") or "").strip()
    if explicit:
        return explicit
    match = TEAM_ID_RE.search(str(row.get(f"{side}_team_logo_url") or ""))
    return match.group(1) if match else ""


def season_from_fixtures(fixtures, default):
    values = []
    for row in fixtures:
        raw = str(row.get("season") or "").strip()
        if raw.isdigit():
            values.append(int(raw))
    return str(max(values)) if values else str(default)


def roster_teams(rosters):
    grouped = {}
    for row in rosters:
        tid = str(row.get("team_id") or "").strip()
        pid = str(row.get("player_id") or "").strip()
        if not tid or not pid:
            continue
        item = grouped.setdefault(tid, {
            "team_id": tid,
            "team_name": str(row.get("team_name") or "").strip(),
            "player_ids": set(),
        })
        item["player_ids"].add(pid)
    return grouped


def parse_iso_utc(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def candidate_teams(rosters, existing, season, fixtures, limit, *, now, refresh_days):
    teams = roster_teams(rosters)
    covered = {}
    latest_capture = {}
    for row in existing:
        if str(row.get("season") or "").strip() != str(season):
            continue
        tid = str(row.get("team_id") or "").strip()
        pid = str(row.get("player_id") or "").strip()
        if tid and pid:
            covered.setdefault(tid, set()).add(pid)
        captured = parse_iso_utc(row.get("captured_at_utc"))
        if tid and captured and (tid not in latest_capture or captured > latest_capture[tid]):
            latest_capture[tid] = captured

    league_by_team = {}
    for row in fixtures:
        league = str(row.get("provider_league_id") or "").strip()
        for side in ("home","away"):
            tid = team_id_from_fixture(row, side)
            if tid:
                league_by_team[tid] = league

    big5 = {"39","61","78","135","140"}
    pending = []
    refresh_cutoff = now - timedelta(days=max(0, int(refresh_days)))
    for tid, item in teams.items():
        missing = item["player_ids"] - covered.get(tid, set())
        if not missing:
            continue
        last_capture = latest_capture.get(tid)
        if last_capture is not None and last_capture > refresh_cutoff:
            continue
        pending.append({
            "team_id": tid,
            "team_name": item["team_name"],
            "missing_roster_players": len(missing),
            "roster_players": len(item["player_ids"]),
            "league_id": league_by_team.get(tid, ""),
            "last_profile_capture_at_utc": iso(last_capture) if last_capture else "",
        })
    pending.sort(key=lambda x: (
        0 if x["league_id"] in big5 else 1,
        -x["missing_roster_players"],
        x["team_name"],
        x["team_id"],
    ))
    return pending[:max(0, int(limit))]


class PageBudget:
    def __init__(self, get, state, now, *, max_calls, daily_limit, protected_calls, checkpoint):
        self.get = get
        self.state = state
        self.max_calls = max(0, int(max_calls))
        self.daily_limit = max(0, int(daily_limit))
        self.protected_calls = max(0, int(protected_calls))
        self.checkpoint = checkpoint
        self.calls = 0
        day = now.date().isoformat()
        if state.get("api_day") != day:
            state.update(api_day=day, api_day_calls=0)

    def __call__(self, path, params, **kwargs):
        protected_limit = max(0, self.daily_limit - self.protected_calls)
        if self.calls >= self.max_calls:
            raise audit.ProtectedBudgetError("Stage80 player-profile per-run API limit reached")
        if int(self.state.get("api_day_calls") or 0) >= protected_limit:
            raise audit.ProtectedBudgetError("Stage80 player-profile protected daily reserve reached")
        self.calls += 1
        self.state["api_day_calls"] = int(self.state.get("api_day_calls") or 0) + 1
        if self.checkpoint:
            self.checkpoint(self.state)
        payload = self.get(path, params, **kwargs)
        if not isinstance(payload, dict) or payload.get("errors") or not isinstance(payload.get("response"), list):
            raise RuntimeError("Missing/invalid API-Football player-profile response")
        return payload


def protected_calls(now):
    live = audit.live_forecast(FIXTURES, now)
    current_round = audit.current_round_forecast(
        now,
        calls_per_run=int(os.getenv("STAGE80_PROFILE_CURRENT_ROUND_CALLS_PER_RUN","60")),
    )
    standings = max(0, int(os.getenv("STAGE80_PROFILE_STANDINGS_RESERVE_CALLS","32")))
    safety = max(0, int(os.getenv("STAGE80_PROFILE_SAFETY_RESERVE_CALLS","100")))
    return {
        "live": int(live.get("reserved_live_calls") or 0),
        "current_round": int(current_round),
        "standings": standings,
        "safety": safety,
        "total": int(live.get("reserved_live_calls") or 0) + int(current_round) + standings + safety,
    }


def normalize_page(payload, requested_team, season, captured_at):
    rows = []
    for item in payload.get("response") or []:
        if not isinstance(item, dict):
            continue
        player = item.get("player") or {}
        pid = str(player.get("id") or "").strip()
        if not pid:
            continue
        birth = player.get("birth") or {}
        stats = item.get("statistics") or []
        team = {}
        for stat in stats:
            candidate = (stat or {}).get("team") or {}
            if str(candidate.get("id") or "").strip() == str(requested_team["team_id"]):
                team = candidate
                break
        if not team and stats:
            team = (stats[0] or {}).get("team") or {}
        rows.append({
            "team_id": str(team.get("id") or requested_team["team_id"]),
            "team_name": team.get("name") or requested_team.get("team_name") or "",
            "season": str(season),
            "player_id": pid,
            "player_name": player.get("name") or "",
            "firstname": player.get("firstname") or "",
            "lastname": player.get("lastname") or "",
            "birth_date": birth.get("date") or "",
            "birth_place": birth.get("place") or "",
            "birth_country": birth.get("country") or "",
            "nationality": player.get("nationality") or "",
            "height": player.get("height") or "",
            "weight": player.get("weight") or "",
            "injured": "" if player.get("injured") is None else str(bool(player.get("injured"))).lower(),
            "photo_url": player.get("photo") or "",
            "captured_at_utc": captured_at,
            "source": "api-football:/players?team&season",
        })
    return rows


def capture_team(team, season, get_page, max_pages, captured_at):
    all_rows = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        if page > max_pages:
            raise RuntimeError(f"team {team['team_id']} exceeds max_pages={max_pages}")
        payload = get_page(
            "/players",
            {"team": team["team_id"], "season": season, "page": page},
            ttl_seconds=30*24*3600,
            force_refresh=False,
        )
        paging = payload.get("paging") or {}
        try:
            total_pages = max(1, int(paging.get("total") or 1))
        except (TypeError, ValueError):
            total_pages = 1
        all_rows.extend(normalize_page(payload, team, season, captured_at))
        page += 1

    dedup = {}
    for row in all_rows:
        key = (row["team_id"], row["season"], row["player_id"])
        dedup[key] = row
    return [dedup[key] for key in sorted(dedup)]


def merge_rows(existing, incoming):
    merged = {
        (str(r.get("team_id") or ""), str(r.get("season") or ""), str(r.get("player_id") or "")): dict(r)
        for r in existing
        if r.get("team_id") and r.get("season") and r.get("player_id")
    }
    for row in incoming:
        key = (row["team_id"], row["season"], row["player_id"])
        merged[key] = dict(row)
    return [merged[key] for key in sorted(merged)]


def main():
    now = datetime.now(timezone.utc)
    rosters = read_csv(ROSTERS)
    fixtures = read_csv(FIXTURES)
    existing = read_csv(OUT)
    season = os.getenv("API_FOOTBALL_SEASON","").strip() or season_from_fixtures(fixtures, now.year)
    max_calls = int(os.getenv("STAGE80_PROFILE_MAX_API_CALLS","24"))
    max_teams = int(os.getenv("STAGE80_PROFILE_MAX_TEAMS","8"))
    max_pages = int(os.getenv("STAGE80_PROFILE_MAX_PAGES_PER_TEAM","4"))
    daily_limit = int(os.getenv("STAGE71_MAX_DAILY_API_CALLS","7000"))
    refresh_days = int(os.getenv("STAGE80_PROFILE_REFRESH_DAYS","7"))

    state = audit.read(SHARED_STATE)
    reserve = protected_calls(now)
    budget = PageBudget(
        s53.api_get,
        state,
        now,
        max_calls=max_calls,
        daily_limit=daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(SHARED_STATE, value),
    )

    candidates = candidate_teams(
        rosters,
        existing,
        season,
        fixtures,
        max_teams,
        now=now,
        refresh_days=refresh_days,
    )
    incoming = []
    completed = []
    warnings = []
    deferred = 0
    for index, team in enumerate(candidates):
        try:
            rows = capture_team(team, season, budget, max_pages, iso(now))
        except audit.ProtectedBudgetError as exc:
            deferred = len(candidates) - index
            warnings.append(str(exc))
            break
        except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            warnings.append(f"{team['team_id']} {team.get('team_name')}: {exc}")
            continue
        if not rows:
            warnings.append(f"{team['team_id']} {team.get('team_name')}: provider returned no usable profile rows")
            continue
        incoming.extend(rows)
        completed.append({
            "team_id": team["team_id"],
            "team_name": team.get("team_name"),
            "profile_rows": len(rows),
        })

    merged = merge_rows(existing, incoming)
    if merged or OUT.exists():
        write_csv(OUT, merged)
    audit.save(SHARED_STATE, state)

    roster_ids = {str(r.get("player_id") or "").strip() for r in rosters if r.get("player_id")}
    profile_ids = {str(r.get("player_id") or "").strip() for r in merged if r.get("player_id")}
    meta = {
        "version": "PBK_STAGE80_PLAYER_PROFILE_ENRICHMENT_V1",
        "run_at_utc": iso(now),
        "status": "ATTENTION" if warnings else ("WAITING" if deferred else "OK"),
        "season": season,
        "provider_endpoint": "/players?team&season",
        "refresh_days": refresh_days,
        "provider_calls": budget.calls,
        "daily_api_calls": int(state.get("api_day_calls") or 0),
        "protected_calls": reserve,
        "candidate_teams": len(candidates),
        "completed_teams": completed,
        "deferred_teams": deferred,
        "profile_rows": len(merged),
        "unique_profile_players": len(profile_ids),
        "current_roster_players": len(roster_ids),
        "current_roster_player_coverage_pct": round(100*len(roster_ids & profile_ids)/len(roster_ids),2) if roster_ids else None,
        "warnings": warnings,
        "provider_polling_frontend": False,
        "research_only": True,
        "identity_enrichment_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
