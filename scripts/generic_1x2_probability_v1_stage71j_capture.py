#!/usr/bin/env python3
"""Zero-extra-call Stage71J adapter for Generic 1X2 v1 forward capture.

Consumes only the fixture and unfiltered /odds payloads already fetched by
Stage71J. It never calls API-Football itself. Only complete Bet365 Match Winner
(H/D/A) vectors with an explicit provider update timestamp are eligible.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

try:
    import generic_1x2_probability_v1_forward as fwd
except ModuleNotFoundError:  # package import in unit tests
    from scripts import generic_1x2_probability_v1_forward as fwd

BOOKMAKER = "Bet365"
MATCH_WINNER_BET_ID = 1
SOURCE = "API-Football /odds Bet365 Match Winner"
META_NAME = "generic_1x2_v1_stage71j_last_run.json"


def _norm(value):
    return " ".join(str(value or "").strip().lower().replace("-", " ").split())


def _num(value):
    return fwd.fnum(value)


def _params(key):
    if not isinstance(key, tuple) or len(key) != 2:
        return {}
    try:
        return {str(k): str(v) for k, v in key[1]}
    except (TypeError, ValueError):
        return {}


def _iso(value):
    parsed = fwd.parse_iso(value)
    return None if parsed is None else parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _outcome_label(value):
    token = _norm(value)
    mapping = {
        "home": "H", "1": "H",
        "draw": "D", "x": "D",
        "away": "A", "2": "A",
    }
    return mapping.get(token)


def _complete_bet365_match_winner(payload, processed_at):
    """Return earliest complete Bet365 1X2 vector in this provider payload."""
    process_dt = fwd.parse_iso(processed_at)
    if process_dt is None:
        raise ValueError("aware process timestamp required")
    candidates = []
    for item in (payload or {}).get("response", []) or []:
        update = _iso(item.get("update"))
        update_dt = fwd.parse_iso(update)
        if update_dt is None or update_dt > process_dt:
            continue
        for bookmaker in item.get("bookmakers", []) or []:
            if _norm(bookmaker.get("name")) != _norm(BOOKMAKER):
                continue
            for bet in bookmaker.get("bets", []) or []:
                try:
                    bet_id = int(bet.get("id") or 0)
                except (TypeError, ValueError):
                    continue
                if bet_id != MATCH_WINNER_BET_ID:
                    continue
                prices = {}
                for value in bet.get("values", []) or []:
                    label = _outcome_label(value.get("value"))
                    odd = _num(value.get("odd"))
                    if label and odd is not None and odd > 1.0 and label not in prices:
                        prices[label] = odd
                if all(label in prices for label in ("H", "D", "A")):
                    candidates.append((update_dt, update, prices))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    _, update, prices = candidates[0]
    return {
        "observed_at_utc": update,
        "b365_home": prices["H"],
        "b365_draw": prices["D"],
        "b365_away": prices["A"],
    }


def rows_from_stage71j_cache(cache, leagues, processed_at):
    """Build forward rows from Stage71J's already-populated request cache."""
    league_by_id = {str(league_id): league for league, league_id in leagues.items()}
    fixtures = {}
    diagnostics = Counter()

    for key, payload in cache.items():
        if not isinstance(key, tuple) or not key or key[0] != "/fixtures":
            continue
        params = _params(key)
        league = league_by_id.get(params.get("league"))
        if league is None:
            continue
        for item in (payload or {}).get("response", []) or []:
            fixture = item.get("fixture") or {}
            teams = item.get("teams") or {}
            fixture_id = str(fixture.get("id") or "").strip()
            kickoff = _iso(fixture.get("date"))
            if not fixture_id or not kickoff:
                diagnostics["fixture_metadata_invalid"] += 1
                continue
            fixtures[fixture_id] = {
                "fixture_id": fixture_id,
                "league": league,
                "home_team": str((teams.get("home") or {}).get("name") or "").strip(),
                "away_team": str((teams.get("away") or {}).get("name") or "").strip(),
                "kickoff_utc": kickoff,
            }

    odds_by_fixture = {}
    for key, payload in cache.items():
        if not isinstance(key, tuple) or not key or key[0] != "/odds":
            continue
        params = _params(key)
        if set(params) != {"fixture"}:
            continue
        fixture_id = str(params.get("fixture") or "").strip()
        if fixture_id:
            odds_by_fixture[fixture_id] = payload

    rows = []
    diagnostics["fixture_metadata"] = len(fixtures)
    diagnostics["unfiltered_odds_payloads"] = len(odds_by_fixture)
    for fixture_id in sorted(fixtures):
        payload = odds_by_fixture.get(fixture_id)
        if payload is None:
            diagnostics["missing_odds_payload"] += 1
            continue
        vector = _complete_bet365_match_winner(payload, processed_at)
        if vector is None:
            diagnostics["missing_complete_bet365_match_winner"] += 1
            continue
        row = dict(fixtures[fixture_id])
        row.update(vector)
        row["source"] = SOURCE
        rows.append(row)
    diagnostics["complete_candidate_rows"] = len(rows)
    return rows, dict(diagnostics)


def capture_rows(rows, cfg, ops_dir, process_time):
    """Append eligible rows to the existing Generic forward journal."""
    ops_dir = Path(ops_dir)
    prematch_path, settlement_path, report_path = fwd.output_paths(ops_dir, cfg)
    prematch_raw, prematch = fwd.read_jsonl(prematch_path)
    _, settlements = fwd.read_jsonl(settlement_path)
    added, rejected = fwd.freeze_observations(rows, cfg, prematch, process_time=process_time)
    fwd.atomic_append_jsonl(prematch_path, prematch_raw, added)
    prematch = prematch + added
    report = fwd.performance_report(cfg, prematch, settlements)
    fwd.atomic_write_json(report_path, report)
    return {
        "candidate_rows": len(rows),
        "observations_added": len(added),
        "observations_rejected": len(rejected),
        "prematch_frozen": len(prematch),
        "settled_rows": len(settlements),
        "rejections": rejected,
        "forward_report_status": report.get("status"),
    }


def capture_from_stage71j_cache(cache, leagues, ops_dir, process_time=None, config_path=fwd.DEFAULT_CFG):
    process_time = process_time or fwd.now_iso()
    if fwd.parse_iso(process_time) is None:
        raise ValueError("aware process timestamp required")
    cfg, _ = fwd.load_contract(config_path)
    rows, extraction = rows_from_stage71j_cache(cache, leagues, process_time)
    result = capture_rows(rows, cfg, ops_dir, process_time)
    payload = {
        "run_at_utc": process_time,
        "status": "OK",
        "mode": "STAGE71J_ZERO_EXTRA_CALL_PROSPECTIVE_CAPTURE",
        "source": SOURCE,
        "bookmaker": BOOKMAKER,
        "bet_id": MATCH_WINNER_BET_ID,
        "api_calls_added": 0,
        "historical_backfill": "FORBIDDEN",
        "settlement_performed": False,
        "extraction": extraction,
        **result,
    }
    fwd.atomic_write_json(Path(ops_dir) / META_NAME, payload)
    return payload


def main():
    raise SystemExit("This adapter is invoked inside Stage71J and must not call the provider directly.")


if __name__ == "__main__":
    main()
