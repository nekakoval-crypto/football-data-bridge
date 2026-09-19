#!/usr/bin/env python3
"""Stage80 — resumable national-team fixture backfill for PBK player-duty research.

Consumes the explicit international-duty source allowlist and captures one
API-Football /fixtures?league&season payload per allowlisted competition-season.

This layer establishes factual national-team fixture history only. It does NOT
infer that any PBK player was called up, travelled, appeared, started, or played.
Player-level evidence is a later /fixtures/players (and lineup where needed)
backfill joined through direct player identity.

Safety / governance:
- shared Stage71 daily API budget with protected operational reserve;
- shared API-Football broker + raw S3/R2 archive;
- resumable cell state;
- fixture-id conflict detection across competition-season cells;
- no betting/model/probability/eligibility/stake/forward authority.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError, api_get, get_broker

OPS = Path(os.getenv("OPS_DIR", "ops"))
ALLOWLIST = OPS / "international_duty_source_allowlist.csv"
ARCHIVE = OPS / "international_team_fixture_history.csv"
QUERY_STATE = OPS / "stage80_international_duty_fixture_backfill_state.csv"
META = OPS / "stage80_international_duty_fixture_backfill_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_FIXTURE_BACKFILL_V1"
FINAL_STATUSES = {"FT", "AET", "PEN"}

ARCHIVE_FIELDS = [
    "fixture_id","provider_league_id","competition_name","candidate_family",
    "season","round","kickoff_utc","status","elapsed",
    "venue_id","venue_name","venue_city",
    "home_team_id","home_team","away_team_id","away_team",
    "home_goals","away_goals","result",
    "evidence_tier","direct_matchday_squad_evidence_possible",
    "direct_minutes_evidence_possible","player_evidence_backfill_eligible",
    "captured_at_utc","source",
    "historical_callup_evidence_possible","nationality_inference_allowed",
    "historical_backfill_only","research_only","operational_betting_authority",
    "creates_signal","probability_mutation","eligibility_mutation",
    "stake_changes","forward_journal_mutation",
]

STATE_FIELDS = [
    "provider_league_id","competition_name","candidate_family","season",
    "season_start","season_end","evidence_tier","fixture_backfill_priority",
    "direct_matchday_squad_evidence_possible",
    "direct_minutes_evidence_possible","player_evidence_backfill_eligible",
    "status","attempt_count","last_attempt_at_utc",
    "fixture_rows","finished_fixture_rows","error",
]

TERMINAL_CELL_STATUSES = {"CAPTURED"}


def iso_now(now=None):
    now = now or datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


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


def btrue(value):
    return str(value or "").strip().lower() in {"1","true","yes","y"}


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def cell_key(row):
    return (sval(row, "provider_league_id"), sval(row, "season"))


def archive_key(row):
    return sval(row, "fixture_id")


def priority_tuple(row):
    try:
        priority = int(sval(row, "fixture_backfill_priority") or "99")
    except ValueError:
        priority = 99
    try:
        season = int(sval(row, "season") or "0")
    except ValueError:
        season = 0
    try:
        league = int(sval(row, "provider_league_id") or "999999999")
    except ValueError:
        league = 999999999
    return (priority, -season, league)


def validate_allowlist(rows):
    valid = []
    invalid = []
    seen = set()
    for row in rows:
        key = cell_key(row)
        ok = bool(
            all(key)
            and key not in seen
            and sval(row, "competition_name")
            and sval(row, "candidate_family")
            and sval(row, "evidence_tier") in {
                "DIRECT_MINUTES","DIRECT_MATCHDAY_SQUAD","FIXTURE_ONLY"
            }
            and sval(row, "pbk_source_selection_status") == "EXPLICIT_ALLOWLIST"
            and sval(row, "historical_callup_evidence_possible") == "false"
            and sval(row, "nationality_inference_allowed") == "false"
            and sval(row, "research_only") == "true"
            and sval(row, "operational_betting_authority") == "false"
            and sval(row, "creates_signal") == "false"
            and sval(row, "probability_mutation") == "false"
            and sval(row, "eligibility_mutation") == "false"
            and sval(row, "stake_changes") == "false"
            and sval(row, "forward_journal_mutation") == "false"
        )
        if ok:
            seen.add(key)
            valid.append(row)
        else:
            invalid.append(row)
    valid.sort(key=priority_tuple)
    return valid, invalid


def state_rows_for_allowlist(allowlist_rows, existing_rows):
    existing = {cell_key(r): dict(r) for r in existing_rows if all(cell_key(r))}
    rows = []
    for spec in sorted(allowlist_rows, key=priority_tuple):
        key = cell_key(spec)
        row = {field: "" for field in STATE_FIELDS}
        row.update(existing.get(key, {}))
        row.update({
            "provider_league_id": key[0],
            "competition_name": sval(spec, "competition_name"),
            "candidate_family": sval(spec, "candidate_family"),
            "season": key[1],
            "season_start": sval(spec, "season_start"),
            "season_end": sval(spec, "season_end"),
            "evidence_tier": sval(spec, "evidence_tier"),
            "fixture_backfill_priority": sval(spec, "fixture_backfill_priority"),
            "direct_matchday_squad_evidence_possible": sval(
                spec, "direct_matchday_squad_evidence_possible"
            ),
            "direct_minutes_evidence_possible": sval(
                spec, "direct_minutes_evidence_possible"
            ),
            "player_evidence_backfill_eligible": sval(
                spec, "player_evidence_backfill_eligible"
            ),
        })
        if not sval(row, "status"):
            row["status"] = "PENDING"
        if not sval(row, "attempt_count"):
            row["attempt_count"] = "0"
        rows.append(row)
    return rows


def result_code(status, home_goals, away_goals):
    if status not in FINAL_STATUSES or home_goals is None or away_goals is None:
        return ""
    if home_goals > away_goals:
        return "H"
    if home_goals < away_goals:
        return "A"
    return "D"


def normalize_payload(payload, spec, captured_at):
    rows = []
    for item in payload.get("response") or []:
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        score_status = fixture.get("status") or {}
        venue = fixture.get("venue") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}

        fixture_id = str(fixture.get("id") or "").strip()
        if not fixture_id:
            continue

        provider_league_id = str(league.get("id") or spec["provider_league_id"]).strip()
        provider_season = str(league.get("season") or spec["season"]).strip()
        if provider_league_id != str(spec["provider_league_id"]) or provider_season != str(spec["season"]):
            raise ValueError(
                f"provider cell drift for fixture {fixture_id}: "
                f"{provider_league_id}/{provider_season} != "
                f"{spec['provider_league_id']}/{spec['season']}"
            )

        home_goals = as_int(goals.get("home"))
        away_goals = as_int(goals.get("away"))
        status = str(score_status.get("short") or "").strip()

        rows.append({
            "fixture_id": fixture_id,
            "provider_league_id": provider_league_id,
            "competition_name": str(league.get("name") or spec["competition_name"]).strip(),
            "candidate_family": str(spec["candidate_family"]),
            "season": provider_season,
            "round": str(league.get("round") or ""),
            "kickoff_utc": str(fixture.get("date") or ""),
            "status": status,
            "elapsed": "" if score_status.get("elapsed") is None else score_status.get("elapsed"),
            "venue_id": str(venue.get("id") or ""),
            "venue_name": str(venue.get("name") or ""),
            "venue_city": str(venue.get("city") or ""),
            "home_team_id": str(home.get("id") or ""),
            "home_team": str(home.get("name") or ""),
            "away_team_id": str(away.get("id") or ""),
            "away_team": str(away.get("name") or ""),
            "home_goals": "" if home_goals is None else home_goals,
            "away_goals": "" if away_goals is None else away_goals,
            "result": result_code(status, home_goals, away_goals),
            "evidence_tier": str(spec["evidence_tier"]),
            "direct_matchday_squad_evidence_possible": str(
                spec["direct_matchday_squad_evidence_possible"]
            ),
            "direct_minutes_evidence_possible": str(
                spec["direct_minutes_evidence_possible"]
            ),
            "player_evidence_backfill_eligible": str(
                spec["player_evidence_backfill_eligible"]
            ),
            "captured_at_utc": captured_at,
            "source": "API-Football /fixtures?league&season",
            "historical_callup_evidence_possible": "false",
            "nationality_inference_allowed": "false",
            "historical_backfill_only": "true",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })
    return rows


def merge_archive(existing, incoming):
    merged = {}
    for row in existing:
        key = archive_key(row)
        if key:
            merged[key] = dict(row)

    for row in incoming:
        key = archive_key(row)
        if not key:
            continue
        old = merged.get(key)
        if old and (
            sval(old, "provider_league_id") != sval(row, "provider_league_id")
            or sval(old, "season") != sval(row, "season")
        ):
            raise ValueError(
                f"fixture id {key} conflicts across competition-season cells: "
                f"{sval(old,'provider_league_id')}/{sval(old,'season')} vs "
                f"{sval(row,'provider_league_id')}/{sval(row,'season')}"
            )
        merged[key] = dict(row)

    return sorted(
        merged.values(),
        key=lambda r: (sval(r, "kickoff_utc"), sval(r, "fixture_id")),
    )


def protected_calls():
    return max(0, int(os.getenv("STAGE80_INTL_DUTY_FIXTURE_PROTECTED_CALLS", "512")))


def run(
    allowlist_path=ALLOWLIST,
    archive_path=ARCHIVE,
    state_path=QUERY_STATE,
    meta_path=META,
    shared_state_path=SHARED_STATE,
    get=api_get,
    now=None,
    max_calls=None,
):
    now = now or datetime.now(timezone.utc)
    max_calls = (
        int(max_calls)
        if max_calls is not None
        else int(os.getenv("STAGE80_INTL_DUTY_FIXTURE_MAX_API_CALLS", "20"))
    )

    raw_allowlist = read_csv(allowlist_path)
    allowlist, invalid_allowlist = validate_allowlist(raw_allowlist)
    if invalid_allowlist:
        raise ValueError(f"invalid allowlist rows: {len(invalid_allowlist)}")
    if len(allowlist) != 80:
        raise ValueError(f"expected 80 allowlisted competition-season rows, got {len(allowlist)}")
    if len({cell_key(r) for r in allowlist}) != 80:
        raise ValueError("allowlist competition-season keys are not unique")

    existing_archive = read_csv(archive_path)
    state = state_rows_for_allowlist(allowlist, read_csv(state_path))
    specs = {cell_key(r): r for r in allowlist}

    shared = audit.read(Path(shared_state_path))
    budget = audit.Budget(
        get,
        shared,
        now,
        limit=max_calls,
        daily_limit=int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "7000")),
        checkpoint=lambda s: audit.save(Path(shared_state_path), s),
        protected_calls=protected_calls(),
    )

    calls_before = int(shared.get("api_day_calls") or 0)
    archive = existing_archive
    warnings = []
    attempted_cells = 0

    for row in state:
        if sval(row, "status") in TERMINAL_CELL_STATUSES:
            continue
        if budget.calls >= max_calls:
            break

        spec = specs[cell_key(row)]
        attempted = iso_now()
        attempted_cells += 1
        try:
            payload = budget(
                "/fixtures",
                {
                    "league": spec["provider_league_id"],
                    "season": spec["season"],
                },
                ttl_seconds=365 * 24 * 3600,
                force_refresh=False,
            )
            normalized = normalize_payload(payload, spec, attempted)
            if not normalized:
                raise RuntimeError("provider returned no fixtures for allowlisted season")

            archive = merge_archive(archive, normalized)
            row["status"] = "CAPTURED"
            row["fixture_rows"] = str(len(normalized))
            row["finished_fixture_rows"] = str(
                sum(sval(r, "status") in FINAL_STATUSES for r in normalized)
            )
            row["error"] = ""
        except audit.ProtectedBudgetError as exc:
            warnings.append(str(exc))
            break
        except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            row["status"] = "ERROR"
            row["error"] = str(exc)
            warnings.append(
                f"{spec['provider_league_id']}:{spec['season']}: {exc}"
            )
        finally:
            if sval(row, "last_attempt_at_utc") != attempted:
                try:
                    row["attempt_count"] = str(int(sval(row, "attempt_count") or "0") + 1)
                except ValueError:
                    row["attempt_count"] = "1"
                row["last_attempt_at_utc"] = attempted
            write_csv(archive_path, ARCHIVE_FIELDS, archive)
            write_csv(state_path, STATE_FIELDS, state)

    audit.save(Path(shared_state_path), shared)

    captured_cells = [r for r in state if sval(r, "status") == "CAPTURED"]
    error_cells = [r for r in state if sval(r, "status") == "ERROR"]
    pending_cells = [r for r in state if sval(r, "status") == "PENDING"]
    archive_ids = {archive_key(r) for r in archive if archive_key(r)}
    duplicates = len([r for r in archive if archive_key(r)]) - len(archive_ids)
    invalid_archive_rows = sum(
        not (
            archive_key(r)
            and sval(r, "provider_league_id")
            and sval(r, "season")
            and sval(r, "kickoff_utc")
            and sval(r, "home_team_id")
            and sval(r, "away_team_id")
            and sval(r, "historical_callup_evidence_possible") == "false"
            and sval(r, "nationality_inference_allowed") == "false"
            and sval(r, "historical_backfill_only") == "true"
            and sval(r, "research_only") == "true"
            and sval(r, "operational_betting_authority") == "false"
            and sval(r, "creates_signal") == "false"
            and sval(r, "probability_mutation") == "false"
            and sval(r, "eligibility_mutation") == "false"
            and sval(r, "stake_changes") == "false"
            and sval(r, "forward_journal_mutation") == "false"
        )
        for r in archive
    )

    broker_stats = get_broker().stats() if get is api_get else {}
    tier_state = defaultdict(Counter)
    for row in state:
        tier_state[sval(row, "evidence_tier")][sval(row, "status")] += 1

    meta = {
        "version": VERSION,
        "generated_at_utc": iso_now(),
        "status": "OK" if len(captured_cells) == len(state) and not error_cells else "COLLECTING",
        "allowlist_rows": len(allowlist),
        "state_rows": len(state),
        "captured_cells": len(captured_cells),
        "pending_cells": len(pending_cells),
        "error_cells": len(error_cells),
        "attempted_cells_this_run": attempted_cells,
        "fixture_archive_rows": len(archive),
        "unique_fixture_ids": len(archive_ids),
        "duplicate_fixture_ids": duplicates,
        "invalid_archive_rows": invalid_archive_rows,
        "finished_fixture_rows": sum(
            sval(r, "status") in FINAL_STATUSES for r in archive
        ),
        "fixture_rows_player_evidence_eligible": sum(
            sval(r, "player_evidence_backfill_eligible") == "true" for r in archive
        ),
        "fixture_rows_direct_minutes_tier": sum(
            sval(r, "evidence_tier") == "DIRECT_MINUTES" for r in archive
        ),
        "fixture_rows_direct_matchday_squad_tier": sum(
            sval(r, "evidence_tier") == "DIRECT_MATCHDAY_SQUAD" for r in archive
        ),
        "tier_state_counts": {
            tier: dict(sorted(counts.items()))
            for tier, counts in sorted(tier_state.items())
        },
        "provider_budget_calls": budget.calls,
        "real_api_calls": broker_stats.get("real_api_calls"),
        "daily_api_calls_before": calls_before,
        "daily_api_calls_after": int(shared.get("api_day_calls") or 0),
        "protected_calls": protected_calls(),
        "warnings": warnings,
        "raw_archive_enabled": broker_stats.get("archive_enabled"),
        "raw_archive_backend": broker_stats.get("archive_backend"),
        "raw_archive_observations": broker_stats.get("archive_observations"),
        "raw_archive_errors": broker_stats.get("archive_errors"),
        "historical_callup_evidence_possible": False,
        "nationality_inference_allowed": False,
        "player_appearance_or_minutes_inferred": False,
        "provider_fixture_history_only": True,
        "historical_backfill_only": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "next_stage": (
            "Build a direct player-evidence backlog from finished captured fixtures "
            "whose allowlist tier is DIRECT_MINUTES or DIRECT_MATCHDAY_SQUAD."
        ),
    }
    write_json(meta_path, meta)
    return meta


def main():
    meta = run()
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
