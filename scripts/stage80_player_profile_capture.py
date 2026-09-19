#!/usr/bin/env python3
"""Stage80 — low-priority API-Football player profile enrichment.

Primary path:
- /players?team=<id>&season=<season>

Residual path:
- /players?id=<player_id>&season=<season>
- used only for current-roster IDs still missing after team capture
- current team context comes from PBK current roster, not inferred from season stats

The collector is identity/research enrichment, not betting authority.

Safety:
- shared Stage71 daily state and protected reserve;
- bounded calls/teams/residual players per run;
- complete team pagination required before a team is persisted;
- no partial team evidence is written;
- residual EMPTY results are ledgered and suppressed for a bounded retry TTL;
- transient residual errors remain retryable;
- one durable profile row per team+season+player.
"""
from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError

OPS = Path(os.getenv("OPS_DIR", "ops"))
ROSTERS = OPS / "team_rosters.csv"
FIXTURES = OPS / "current_round_fixtures.csv"
OUT = OPS / "player_profile_evidence.csv"
RESIDUAL_STATE = OPS / "player_profile_residual_state.csv"
INTERNATIONAL_EVIDENCE = OPS / "international_duty_player_evidence.csv"
INTERNATIONAL_STATE = OPS / "player_profile_international_residual_state.csv"
META = OPS / "stage80_player_profile_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

TEAM_ID_RE = re.compile(r"/teams/(\d+)")
TEAM_SOURCE = "api-football:/players?team&season"
RESIDUAL_SOURCE = "api-football:/players?id&season+current_roster"
INTERNATIONAL_SOURCE = "api-football:/players?id&season+international_evidence"

FIELDS = [
    "team_id","team_name","season","player_id","player_name","firstname","lastname",
    "birth_date","birth_place","birth_country","nationality","height","weight",
    "injured","photo_url","captured_at_utc","source",
]
RESIDUAL_FIELDS = [
    "season","player_id","team_id","team_name","status","attempts",
    "last_attempt_at_utc","last_error",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_csv(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def write_csv(path, rows):
    write_rows(path, FIELDS, rows)


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


def fixture_league_by_team(fixtures):
    result = {}
    for row in fixtures:
        league = str(row.get("provider_league_id") or "").strip()
        for side in ("home", "away"):
            tid = team_id_from_fixture(row, side)
            if tid:
                result[tid] = league
    return result


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


def roster_player_contexts(rosters):
    grouped = defaultdict(dict)
    for row in rosters:
        tid = str(row.get("team_id") or "").strip()
        pid = str(row.get("player_id") or "").strip()
        if not tid or not pid:
            continue
        grouped[pid][tid] = {
            "player_id": pid,
            "team_id": tid,
            "team_name": str(row.get("team_name") or "").strip(),
        }
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
        if (
            tid
            and captured
            and str(row.get("source") or "").strip() == TEAM_SOURCE
            and (tid not in latest_capture or captured > latest_capture[tid])
        ):
            latest_capture[tid] = captured

    league_by_team = fixture_league_by_team(fixtures)
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


def residual_candidates(
    rosters,
    existing,
    residual_state,
    season,
    fixtures,
    limit,
    *,
    now,
    retry_days,
):
    existing_ids = {
        str(row.get("player_id") or "").strip()
        for row in existing
        if str(row.get("season") or "").strip() == str(season)
        and str(row.get("player_id") or "").strip()
    }
    latest_state = {}
    for row in residual_state:
        if str(row.get("season") or "").strip() != str(season):
            continue
        pid = str(row.get("player_id") or "").strip()
        attempted = parse_iso_utc(row.get("last_attempt_at_utc"))
        if not pid or attempted is None:
            continue
        previous = latest_state.get(pid)
        if previous is None or attempted > previous[0]:
            latest_state[pid] = (attempted, row)

    contexts = roster_player_contexts(rosters)
    league_by_team = fixture_league_by_team(fixtures)
    big5 = {"39","61","78","135","140"}
    retry_cutoff = now - timedelta(days=max(0, int(retry_days)))

    pending = []
    ambiguous = 0
    suppressed = 0
    for pid, team_map in contexts.items():
        if pid in existing_ids:
            continue
        if len(team_map) != 1:
            ambiguous += 1
            continue

        latest = latest_state.get(pid)
        if latest is not None:
            attempted, state_row = latest
            status = str(state_row.get("status") or "").upper()
            if status in {"EMPTY", "CAPTURED"} and attempted > retry_cutoff:
                suppressed += 1
                continue

        context = next(iter(team_map.values()))
        context = dict(context)
        context["league_id"] = league_by_team.get(context["team_id"], "")
        pending.append(context)

    pending.sort(key=lambda x: (
        0 if x["league_id"] in big5 else 1,
        x["team_name"],
        x["player_id"],
    ))
    return pending[:max(0, int(limit))], {
        "ambiguous_current_roster_player_ids": ambiguous,
        "suppressed_recent_residual_attempts": suppressed,
    }


def international_profile_candidates(
    international_rows,
    existing,
    international_state,
    limit,
    *,
    now,
    retry_days,
):
    """Select direct international player IDs still missing a profile DOB.

    Candidate seasons come only from direct international evidence. For each
    player, try the latest not-recently-terminal evidence season first; if that
    season was EMPTY/NO_DOB recently, the next older evidence season may be
    tried without inventing club context.
    """
    dob_ids = {
        str(row.get("player_id") or "").strip()
        for row in existing
        if str(row.get("player_id") or "").strip()
        and str(row.get("birth_date") or "").strip()
    }
    latest_state = {}
    for row in international_state or []:
        season = str(row.get("season") or "").strip()
        pid = str(row.get("player_id") or "").strip()
        attempted = parse_iso_utc(row.get("last_attempt_at_utc"))
        if not season or not pid or attempted is None:
            continue
        key = (season, pid)
        previous = latest_state.get(key)
        if previous is None or attempted > previous[0]:
            latest_state[key] = (attempted, row)

    by_player = defaultdict(list)
    for row in international_rows or []:
        pid = str(row.get("player_id") or "").strip()
        season = str(row.get("season") or "").strip()
        kickoff = parse_iso_utc(row.get("kickoff_utc"))
        if not pid or not season or pid in dob_ids:
            continue
        by_player[pid].append({
            "player_id": pid,
            "season": season,
            "kickoff": kickoff,
            "player_name": str(row.get("player_name") or "").strip(),
        })

    retry_cutoff = now - timedelta(days=max(0, int(retry_days)))
    pending = []
    suppressed_pairs = 0
    exhausted_players = 0
    for pid, rows in by_player.items():
        rows.sort(
            key=lambda item: (
                item["kickoff"] or datetime.min.replace(tzinfo=timezone.utc),
                item["season"],
            ),
            reverse=True,
        )
        seen_seasons = set()
        chosen = None
        for item in rows:
            season = item["season"]
            if season in seen_seasons:
                continue
            seen_seasons.add(season)
            latest = latest_state.get((season, pid))
            if latest is not None:
                attempted, state_row = latest
                status = str(state_row.get("status") or "").upper()
                if status in {"EMPTY", "NO_DOB", "CAPTURED_DOB"} and attempted > retry_cutoff:
                    suppressed_pairs += 1
                    continue
            chosen = {
                "player_id": pid,
                "team_id": "",
                "team_name": "",
                "season": season,
                "player_name": item["player_name"],
                "latest_evidence_kickoff_utc": (
                    iso(item["kickoff"]) if item["kickoff"] else ""
                ),
            }
            break
        if chosen is None:
            exhausted_players += 1
            continue
        pending.append(chosen)

    pending.sort(
        key=lambda item: (
            parse_iso_utc(item["latest_evidence_kickoff_utc"])
            or datetime.min.replace(tzinfo=timezone.utc),
            item["player_id"],
        ),
        reverse=True,
    )
    return pending[:max(0, int(limit))], {
        "players_already_with_profile_dob": len(dob_ids),
        "suppressed_recent_player_seasons": suppressed_pairs,
        "players_without_retryable_evidence_season": exhausted_players,
    }


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


def profile_row(player, requested_team, season, captured_at, source):
    pid = str(player.get("id") or "").strip()
    if not pid:
        return None
    birth = player.get("birth") or {}
    return {
        "team_id": str(requested_team["team_id"]),
        "team_name": requested_team.get("team_name") or "",
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
        "source": source,
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
        stats = item.get("statistics") or []
        team = {}
        for stat in stats:
            candidate = (stat or {}).get("team") or {}
            if str(candidate.get("id") or "").strip() == str(requested_team["team_id"]):
                team = candidate
                break
        if not team and stats:
            team = (stats[0] or {}).get("team") or {}
        row = profile_row(
            player,
            {
                "team_id": str(team.get("id") or requested_team["team_id"]),
                "team_name": team.get("name") or requested_team.get("team_name") or "",
            },
            season,
            captured_at,
            TEAM_SOURCE,
        )
        if row:
            rows.append(row)
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


def capture_residual_player(candidate, season, get_page, captured_at, source=RESIDUAL_SOURCE):
    payload = get_page(
        "/players",
        {"id": candidate["player_id"], "season": season},
        ttl_seconds=30*24*3600,
        force_refresh=False,
    )
    for item in payload.get("response") or []:
        if not isinstance(item, dict):
            continue
        player = item.get("player") or {}
        if str(player.get("id") or "").strip() != str(candidate["player_id"]):
            continue
        row = profile_row(player, candidate, season, captured_at, source)
        return [row] if row else []
    return []


def update_residual_state(rows, season, candidate, status, attempted_at, error=""):
    key = (str(season), str(candidate["player_id"]))
    indexed = {}
    for row in rows:
        row_key = (
            str(row.get("season") or "").strip(),
            str(row.get("player_id") or "").strip(),
        )
        if all(row_key):
            indexed[row_key] = dict(row)
    previous = indexed.get(key, {})
    try:
        attempts = int(previous.get("attempts") or 0) + 1
    except (TypeError, ValueError):
        attempts = 1
    indexed[key] = {
        "season": str(season),
        "player_id": str(candidate["player_id"]),
        "team_id": str(candidate["team_id"]),
        "team_name": candidate.get("team_name") or "",
        "status": status,
        "attempts": str(attempts),
        "last_attempt_at_utc": attempted_at,
        "last_error": error,
    }
    return [indexed[k] for k in sorted(indexed)]


def merge_rows(existing, incoming):
    merged = {
        (str(r.get("team_id") or ""), str(r.get("season") or ""), str(r.get("player_id") or "")): dict(r)
        for r in existing
        if r.get("season") and r.get("player_id")
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
    residual_state = read_csv(RESIDUAL_STATE)
    international_rows = read_csv(INTERNATIONAL_EVIDENCE)
    international_state = read_csv(INTERNATIONAL_STATE)

    season = os.getenv("API_FOOTBALL_SEASON","").strip() or season_from_fixtures(fixtures, now.year)
    max_calls = int(os.getenv("STAGE80_PROFILE_MAX_API_CALLS","24"))
    max_teams = int(os.getenv("STAGE80_PROFILE_MAX_TEAMS","8"))
    max_pages = int(os.getenv("STAGE80_PROFILE_MAX_PAGES_PER_TEAM","4"))
    max_residual_players = int(os.getenv("STAGE80_PROFILE_MAX_RESIDUAL_PLAYERS","0"))
    max_international_players = int(os.getenv("STAGE80_PROFILE_MAX_INTERNATIONAL_PLAYERS","0"))
    daily_limit = int(os.getenv("STAGE71_MAX_DAILY_API_CALLS","7000"))
    refresh_days = int(os.getenv("STAGE80_PROFILE_REFRESH_DAYS","7"))
    residual_retry_days = int(os.getenv("STAGE80_PROFILE_RESIDUAL_RETRY_DAYS","7"))
    international_retry_days = int(os.getenv("STAGE80_PROFILE_INTERNATIONAL_RETRY_DAYS","30"))

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

    team_candidates = candidate_teams(
        rosters,
        existing,
        season,
        fixtures,
        max_teams,
        now=now,
        refresh_days=refresh_days,
    )
    incoming = []
    completed_teams = []
    warnings = []
    deferred_teams = 0

    for index, team in enumerate(team_candidates):
        try:
            rows = capture_team(team, season, budget, max_pages, iso(now))
        except audit.ProtectedBudgetError as exc:
            deferred_teams = len(team_candidates) - index
            warnings.append(str(exc))
            break
        except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            warnings.append(f"{team['team_id']} {team.get('team_name')}: {exc}")
            continue
        if not rows:
            warnings.append(f"{team['team_id']} {team.get('team_name')}: provider returned no usable profile rows")
            continue
        incoming.extend(rows)
        completed_teams.append({
            "team_id": team["team_id"],
            "team_name": team.get("team_name"),
            "profile_rows": len(rows),
        })

    team_provider_calls = budget.calls
    merged = merge_rows(existing, incoming)

    residual_list, residual_diag = residual_candidates(
        rosters,
        merged,
        residual_state,
        season,
        fixtures,
        max_residual_players,
        now=now,
        retry_days=residual_retry_days,
    )

    residual_captured = 0
    residual_empty = 0
    residual_errors = 0
    residual_deferred = 0
    residual_incoming = []

    if deferred_teams == 0:
        for index, candidate in enumerate(residual_list):
            attempted_at = iso(now)
            try:
                rows = capture_residual_player(
                    candidate,
                    season,
                    budget,
                    attempted_at,
                )
            except audit.ProtectedBudgetError as exc:
                residual_deferred = len(residual_list) - index
                warnings.append(str(exc))
                break
            except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
                residual_errors += 1
                residual_state = update_residual_state(
                    residual_state,
                    season,
                    candidate,
                    "ERROR",
                    attempted_at,
                    str(exc),
                )
                warnings.append(
                    f"residual player {candidate['player_id']} "
                    f"{candidate.get('team_name')}: {exc}"
                )
                continue

            if rows:
                residual_incoming.extend(rows)
                residual_captured += 1
                residual_state = update_residual_state(
                    residual_state,
                    season,
                    candidate,
                    "CAPTURED",
                    attempted_at,
                )
            else:
                residual_empty += 1
                residual_state = update_residual_state(
                    residual_state,
                    season,
                    candidate,
                    "EMPTY",
                    attempted_at,
                )

    merged = merge_rows(merged, residual_incoming)

    international_list, international_diag = international_profile_candidates(
        international_rows,
        merged,
        international_state,
        max_international_players,
        now=now,
        retry_days=international_retry_days,
    )
    international_captured_dob = 0
    international_no_dob = 0
    international_empty = 0
    international_errors = 0
    international_deferred = 0
    international_incoming = []

    if deferred_teams == 0 and residual_deferred == 0:
        for index, candidate in enumerate(international_list):
            attempted_at = iso(now)
            candidate_season = candidate["season"]
            try:
                rows = capture_residual_player(
                    candidate,
                    candidate_season,
                    budget,
                    attempted_at,
                    source=INTERNATIONAL_SOURCE,
                )
            except audit.ProtectedBudgetError as exc:
                international_deferred = len(international_list) - index
                warnings.append(str(exc))
                break
            except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
                international_errors += 1
                international_state = update_residual_state(
                    international_state,
                    candidate_season,
                    candidate,
                    "ERROR",
                    attempted_at,
                    str(exc),
                )
                warnings.append(
                    f"international profile {candidate['player_id']} "
                    f"season {candidate_season}: {exc}"
                )
                continue

            if rows:
                international_incoming.extend(rows)
                has_dob = any(str(row.get("birth_date") or "").strip() for row in rows)
                status = "CAPTURED_DOB" if has_dob else "NO_DOB"
                if has_dob:
                    international_captured_dob += 1
                else:
                    international_no_dob += 1
                international_state = update_residual_state(
                    international_state,
                    candidate_season,
                    candidate,
                    status,
                    attempted_at,
                )
            else:
                international_empty += 1
                international_state = update_residual_state(
                    international_state,
                    candidate_season,
                    candidate,
                    "EMPTY",
                    attempted_at,
                )

    merged = merge_rows(merged, international_incoming)
    if merged or OUT.exists():
        write_csv(OUT, merged)
    if residual_state or RESIDUAL_STATE.exists():
        write_rows(RESIDUAL_STATE, RESIDUAL_FIELDS, residual_state)
    if international_state or INTERNATIONAL_STATE.exists():
        write_rows(INTERNATIONAL_STATE, RESIDUAL_FIELDS, international_state)

    audit.save(SHARED_STATE, state)

    roster_ids = {str(r.get("player_id") or "").strip() for r in rosters if r.get("player_id")}
    profile_ids = {str(r.get("player_id") or "").strip() for r in merged if r.get("player_id")}

    meta = {
        "version": "PBK_STAGE80_PLAYER_PROFILE_ENRICHMENT_V3_INTERNATIONAL_RESIDUAL_DOB",
        "run_at_utc": iso(now),
        "status": "ATTENTION" if warnings else (
            "WAITING" if deferred_teams or residual_deferred else "OK"
        ),
        "season": season,
        "provider_endpoints": [
            "/players?team&season",
            "/players?id&season",
        ],
        "refresh_days": refresh_days,
        "residual_retry_days": residual_retry_days,
        "international_retry_days": international_retry_days,
        "provider_calls": budget.calls,
        "team_provider_calls": team_provider_calls,
        "residual_provider_calls": budget.calls - team_provider_calls,
        "daily_api_calls": int(state.get("api_day_calls") or 0),
        "protected_calls": reserve,
        "candidate_teams": len(team_candidates),
        "completed_teams": completed_teams,
        "deferred_teams": deferred_teams,
        "residual_candidate_players": len(residual_list),
        "residual_captured_players": residual_captured,
        "residual_empty_players": residual_empty,
        "residual_error_players": residual_errors,
        "residual_deferred_players": residual_deferred,
        "residual_ambiguous_current_roster_player_ids": residual_diag[
            "ambiguous_current_roster_player_ids"
        ],
        "residual_suppressed_recent_attempts": residual_diag[
            "suppressed_recent_residual_attempts"
        ],
        "international_evidence_rows": len(international_rows),
        "international_candidate_players": len(international_list),
        "international_captured_dob_players": international_captured_dob,
        "international_no_dob_players": international_no_dob,
        "international_empty_players": international_empty,
        "international_error_players": international_errors,
        "international_deferred_players": international_deferred,
        "international_players_already_with_profile_dob": international_diag[
            "players_already_with_profile_dob"
        ],
        "international_suppressed_recent_player_seasons": international_diag[
            "suppressed_recent_player_seasons"
        ],
        "international_players_without_retryable_evidence_season": international_diag[
            "players_without_retryable_evidence_season"
        ],
        "profile_rows": len(merged),
        "unique_profile_players": len(profile_ids),
        "current_roster_players": len(roster_ids),
        "current_roster_player_coverage_pct": (
            round(100 * len(roster_ids & profile_ids) / len(roster_ids), 2)
            if roster_ids else None
        ),
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
    META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
