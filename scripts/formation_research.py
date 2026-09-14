"""Provider-free append-only formation observations. Never consumed by strategy code."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from lineup_context import build_lineup_context, _dict_rows, _table_exists, _parse_utc


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def read_events(path):
    path = Path(path)
    if not path.exists():
        return []
    # Fail closed on corruption; never rewrite or silently skip audit evidence.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def result_for(fixture):
    source = str(fixture.get("source_status") or "").upper()
    scores = [fixture.get("score_home"), fixture.get("score_away")]
    valid = all(re.fullmatch(r"[0-9]{1,3}", str(v)) for v in scores)
    if source != "FT" or not valid:
        return {"status": "UNKNOWN", "source_status": source or None, "score": None}
    home, away = map(int, scores)
    return {"status": "FT", "source_status": source, "score": [home, away],
            "outcome": "HOME" if home > away else "AWAY" if away > home else "DRAW"}


def capture(conn, path, observed_at_utc):
    """Append changed context/results from the existing projection; preserve prior bytes."""
    events = read_events(path)
    seen = {event["event_id"] for event in events}
    additions = []

    def add(value):
        event_id = hashlib.sha256(encode(value).encode()).hexdigest()
        if event_id not in seen:
            seen.add(event_id)
            additions.append({**value, "event_id": event_id, "recorded_at_utc": observed_at_utc})

    if _table_exists(conn, "current_round_matches"):
        for fixture in _dict_rows(conn.execute("SELECT * FROM current_round_matches")):
            fid = str(fixture.get("fixture_id") or "")
            code, lineup = build_lineup_context(conn, fid)
            if code != 200:
                continue
            identity = {key: fixture.get(key) for key in (
                "kickoff_utc", "provider_league_id", "league_name", "season", "home_team", "away_team")}
            identity["fixture_id"] = fid
            # Retain both expected and official observations even when official wins display.
            for kind in ("expected", "official"):
                teams = {}
                for side in ("home", "away"):
                    team = lineup.get(side) or {}
                    evidence = team.get(kind) or {}
                    if not evidence:
                        continue
                    teams[side] = {
                        "team_id": team.get("team_id"), "team_name": team.get("team_name"),
                        "formation": evidence.get("formation"), "coach": evidence.get("coach"),
                        "status": kind.upper(), "captured_at_utc": evidence.get("captured_at_utc"),
                        "source": evidence.get("source"),
                        "basis_fixtures": evidence.get("basis_fixtures"),
                    }
                if teams:
                    add({**identity, "kind": "lineup", "teams": teams,
                         "formation_matchup": [teams.get(s, {}).get("formation") for s in ("home", "away")]})
            result = result_for(fixture)
            # Keep unknown/cancelled/invalid outcomes explicit. Scores never settle bets here.
            add({**identity, "kind": "result", "result": result,
                 "source_observed_at_utc": fixture.get("live_observed_at_utc") or fixture.get("observed_at_utc")})
    if additions:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as stream:
            if path.stat().st_size and not path.read_bytes().endswith(b"\n"):
                stream.write(b"\n")
            for event in additions:
                stream.write((encode(event) + "\n").encode())
    return events + additions


def project(conn, events):
    conn.execute("CREATE TABLE formation_research_events (event_id TEXT PRIMARY KEY, fixture_id TEXT, payload_json TEXT NOT NULL)")
    conn.executemany("INSERT INTO formation_research_events VALUES (?,?,?)",
                     [(e["event_id"], e["fixture_id"], encode(e)) for e in events])
    conn.execute("CREATE INDEX idx_formation_fixture ON formation_research_events(fixture_id)")
    return len(events)


def summarize(events, team_id=None, fixture_id=None):
    fixtures = {}
    for event in events:
        fid = event["fixture_id"]
        if fixture_id and str(fixture_id) != fid:
            continue
        item = fixtures.setdefault(fid, {"fixture_id": fid, "teams": {}, "result": {"status": "UNKNOWN"}})
        item.update({k: event.get(k) for k in ("kickoff_utc", "provider_league_id", "league_name", "season")})
        if event["kind"] == "result":
            observed = _parse_utc(event.get("source_observed_at_utc"))
            previous = _parse_utc(item.get("result_observed_at_utc"))
            if previous is None or (observed is not None and observed >= previous):
                item["result"] = event["result"]
                item["result_observed_at_utc"] = event.get("source_observed_at_utc")
            continue
        for side, candidate in event.get("teams", {}).items():
            previous = item["teams"].get(side)
            # Official evidence cannot be downgraded by a subsequent expected snapshot.
            if previous is None or (candidate.get("status") == "OFFICIAL" and previous.get("status") != "OFFICIAL"):
                item["teams"][side] = candidate
            elif candidate.get("status") == previous.get("status"):
                old, new = _parse_utc(previous.get("captured_at_utc")), _parse_utc(candidate.get("captured_at_utc"))
                if new and (not old or new >= old):
                    item["teams"][side] = candidate
    history, matrix = [], {}
    for item in fixtures.values():
        teams = item["teams"]
        if not teams or (team_id and not any(str(t.get("team_id")) == str(team_id) for t in teams.values())):
            continue
        history.append(item)
        home, away = teams.get("home", {}), teams.get("away", {})
        if not home.get("formation") or not away.get("formation"):
            continue
        key = (home["formation"], away["formation"], home["status"], away["status"])
        cell = matrix.setdefault(key, dict(zip(("home_formation", "away_formation", "home_status", "away_status"), key),
                                          matches=0, settled=0, home_wins=0, draws=0, away_wins=0))
        cell["matches"] += 1
        result = item["result"]
        if result.get("status") == "FT":
            cell["settled"] += 1
            cell[{"HOME": "home_wins", "DRAW": "draws", "AWAY": "away_wins"}[result["outcome"]]] += 1
    for cell in matrix.values():
        cell["small_sample"] = cell["settled"] < 10
        cell["home_win_rate"] = cell["home_wins"] / cell["settled"] if cell["settled"] else None
    return {"research_only": True, "provider_polling": False, "probability_mutation": False,
            "eligibility_mutation": False, "stake_changes": False,
            "selection": "latest per team, official before expected; one fixture per matrix cell",
            "history": sorted(history, key=lambda row: (row.get("kickoff_utc") or "", row["fixture_id"])),
            "matrix": list(matrix.values()), "available": bool(history)}


def read_audit(conn, team_id=None, fixture_id=None):
    events = []
    if _table_exists(conn, "formation_research_events"):
        query = "SELECT payload_json FROM formation_research_events"
        args = ()
        if fixture_id:
            query += " WHERE fixture_id=?"
            args = (str(fixture_id),)
        events = [json.loads(row[0]) for row in conn.execute(query + " ORDER BY rowid", args)]
    return summarize(events, team_id, fixture_id)
