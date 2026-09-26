#!/usr/bin/env python3
"""Stage80 — direct historical player evidence capture for international duty.

Consumes the fixed-window international player-evidence backlog.

Endpoint semantics:
- /fixtures/players (DIRECT_MINUTES):
    fixture-specific player row is direct matchday evidence;
    appearance is confirmed only when provider minutes > 0;
    minutes are confirmed only when a numeric minutes field is present;
    starter/substitute appearance uses the provider games.substitute field.
- /fixtures/lineups (DIRECT_MATCHDAY_SQUAD):
    startXI/substitutes are direct matchday-squad listing evidence;
    no appearance or minutes are inferred from lineup listing alone.

Formal federation call-up, travel and return timing remain separate downstream
derivations/evidence layers. This stage never treats nationality as participation.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import stage71_observation_audit as audit
import stage80_international_duty_player_evidence_backlog as queue
from api_football_broker import ApiFootballBrokerError, api_get, get_broker, make_archive_before_budget_get

OPS = Path(os.getenv("OPS_DIR", "ops"))
BACKLOG = OPS / "international_duty_player_evidence_backlog.csv"
BACKLOG_META = OPS / "stage80_international_duty_player_evidence_backlog_last_run.json"
EVIDENCE = OPS / "international_duty_player_evidence.csv"
META = OPS / "stage80_international_duty_player_evidence_capture_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_EVIDENCE_CAPTURE_V2_STRICT_ROLE_SEMANTICS"

EVIDENCE_FIELDS = [
    "fixture_id","provider_league_id","competition_name","candidate_family",
    "season","round","kickoff_utc","window_id",
    "national_team_id","national_team_name",
    "player_id","player_name","position","number","grid",
    "evidence_tier","capture_endpoint","evidence_source_type","lineup_role",
    "minutes","provider_substitute_flag","provider_captain_flag","provider_rating",
    "matchday_squad_confirmed","appearance_confirmed","minutes_confirmed",
    "starter_listed_confirmed","substitute_listed_confirmed",
    "substitute_appearance_confirmed",
    "formal_callup_status","travel_status",
    "captured_at_utc","source",
    "nationality_inference_allowed","travel_inference_allowed",
    "research_only","operational_betting_authority","creates_signal",
    "probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation",
]


def iso_now(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


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


def bool_text(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {"_invalid_json": True}


def write_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def evidence_key(row):
    return (
        sval(row, "fixture_id"),
        sval(row, "national_team_id"),
        sval(row, "player_id"),
    )


def expected_team_ids(backlog_row):
    return {
        sval(backlog_row, "home_team_id"),
        sval(backlog_row, "away_team_id"),
    } - {""}


def common_evidence(backlog_row, team_id, team_name, player_id, player_name, captured_at):
    return {
        "fixture_id": sval(backlog_row, "fixture_id"),
        "provider_league_id": sval(backlog_row, "provider_league_id"),
        "competition_name": sval(backlog_row, "competition_name"),
        "candidate_family": sval(backlog_row, "candidate_family"),
        "season": sval(backlog_row, "season"),
        "round": sval(backlog_row, "round"),
        "kickoff_utc": sval(backlog_row, "kickoff_utc"),
        "window_id": sval(backlog_row, "window_id"),
        "national_team_id": str(team_id or ""),
        "national_team_name": str(team_name or ""),
        "player_id": str(player_id or ""),
        "player_name": str(player_name or ""),
        "evidence_tier": sval(backlog_row, "evidence_tier"),
        "capture_endpoint": sval(backlog_row, "capture_endpoint"),
        "formal_callup_status": "NOT_SEPARATELY_VERIFIED",
        "travel_status": "NOT_DERIVED",
        "captured_at_utc": captured_at,
        "nationality_inference_allowed": "false",
        "travel_inference_allowed": "false",
        "research_only": "true",
        "operational_betting_authority": "false",
        "creates_signal": "false",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }


def validate_team(team_id, backlog_row):
    team_id = str(team_id or "").strip()
    expected = expected_team_ids(backlog_row)
    if not team_id or team_id not in expected:
        raise ValueError(
            f"fixture {sval(backlog_row,'fixture_id')} provider team {team_id!r} "
            f"not in expected national teams {sorted(expected)}"
        )


def normalize_player_stats(payload, backlog_row, captured_at):
    if sval(backlog_row, "capture_endpoint") != "/fixtures/players":
        raise ValueError("player-stats normalizer used for non-player endpoint")

    rows = []
    seen = set()
    for team_block in payload.get("response") or []:
        if not isinstance(team_block, dict):
            continue
        team = team_block.get("team") or {}
        team_id = str(team.get("id") or "").strip()
        team_name = str(team.get("name") or "")
        validate_team(team_id, backlog_row)

        for item in team_block.get("players") or []:
            if not isinstance(item, dict):
                continue
            player = item.get("player") or {}
            player_id = str(player.get("id") or "").strip()
            if not player_id:
                continue
            key = (team_id, player_id)
            if key in seen:
                raise ValueError(
                    f"duplicate fixture-player row for {sval(backlog_row,'fixture_id')}:{team_id}:{player_id}"
                )
            seen.add(key)

            stats_list = item.get("statistics") or []
            stats = stats_list[0] if isinstance(stats_list, list) and stats_list else {}
            games = (stats or {}).get("games") or {}
            minutes = as_int(games.get("minutes"))
            substitute = games.get("substitute")
            captain = games.get("captain")
            appearance = minutes is not None and minutes > 0
            minutes_confirmed = minutes is not None and minutes >= 0
            # /fixtures/players directly proves minutes/appearance, but the
            # provider's games.substitute=False is NOT treated as official XI
            # evidence. Starter/substitute listing belongs to /fixtures/lineups.
            # A direct substitute=True plus positive minutes can still prove a
            # substitute appearance without proving the historical lineup list.
            sub_appearance = appearance and substitute is True

            if sub_appearance:
                role = "SUBSTITUTE_APPEARANCE_PROVIDER_FLAG"
            elif appearance:
                role = "APPEARANCE_ROLE_UNVERIFIED"
            else:
                role = "PLAYER_STATS_LISTED_NO_APPEARANCE"

            row = common_evidence(
                backlog_row, team_id, team_name, player_id,
                player.get("name"), captured_at,
            )
            row.update({
                "position": str(games.get("position") or ""),
                "number": "",
                "grid": "",
                "evidence_source_type": "FIXTURE_PLAYER_STATS",
                "lineup_role": role,
                "minutes": "" if minutes is None else minutes,
                "provider_substitute_flag": bool_text(substitute),
                "provider_captain_flag": bool_text(captain),
                "provider_rating": "" if games.get("rating") is None else games.get("rating"),
                "matchday_squad_confirmed": "true",
                "appearance_confirmed": "true" if appearance else "false",
                "minutes_confirmed": "true" if minutes_confirmed else "false",
                "starter_listed_confirmed": "false",
                "substitute_listed_confirmed": "false",
                "substitute_appearance_confirmed": "true" if sub_appearance else "false",
                "source": "API-Football /fixtures/players",
            })
            rows.append(row)
    return rows


def lineup_player_rows(items, role, backlog_row, team_id, team_name, captured_at, seen):
    rows = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        player = item.get("player") or {}
        player_id = str(player.get("id") or "").strip()
        if not player_id:
            continue
        key = (team_id, player_id)
        if key in seen:
            raise ValueError(
                f"duplicate lineup player for {sval(backlog_row,'fixture_id')}:{team_id}:{player_id}"
            )
        seen.add(key)

        starter = role == "STARTER_LISTED"
        substitute = role == "SUBSTITUTE_LISTED"
        row = common_evidence(
            backlog_row, team_id, team_name, player_id,
            player.get("name"), captured_at,
        )
        row.update({
            "position": str(player.get("pos") or ""),
            "number": "" if player.get("number") is None else player.get("number"),
            "grid": str(player.get("grid") or ""),
            "evidence_source_type": "OFFICIAL_LINEUP",
            "lineup_role": role,
            "minutes": "",
            "provider_substitute_flag": "true" if substitute else "false",
            "provider_captain_flag": "",
            "provider_rating": "",
            "matchday_squad_confirmed": "true",
            "appearance_confirmed": "false",
            "minutes_confirmed": "false",
            "starter_listed_confirmed": "true" if starter else "false",
            "substitute_listed_confirmed": "true" if substitute else "false",
            "substitute_appearance_confirmed": "false",
            "source": "API-Football /fixtures/lineups",
        })
        rows.append(row)
    return rows


def normalize_lineups(payload, backlog_row, captured_at):
    if sval(backlog_row, "capture_endpoint") != "/fixtures/lineups":
        raise ValueError("lineup normalizer used for non-lineup endpoint")

    rows = []
    for team_block in payload.get("response") or []:
        if not isinstance(team_block, dict):
            continue
        team = team_block.get("team") or {}
        team_id = str(team.get("id") or "").strip()
        team_name = str(team.get("name") or "")
        validate_team(team_id, backlog_row)
        seen = set()
        rows.extend(lineup_player_rows(
            team_block.get("startXI"), "STARTER_LISTED",
            backlog_row, team_id, team_name, captured_at, seen,
        ))
        rows.extend(lineup_player_rows(
            team_block.get("substitutes"), "SUBSTITUTE_LISTED",
            backlog_row, team_id, team_name, captured_at, seen,
        ))
    return rows


def normalize_payload(payload, backlog_row, captured_at):
    endpoint = sval(backlog_row, "capture_endpoint")
    if endpoint == "/fixtures/players":
        return normalize_player_stats(payload, backlog_row, captured_at)
    if endpoint == "/fixtures/lineups":
        return normalize_lineups(payload, backlog_row, captured_at)
    raise ValueError(f"unsupported capture endpoint: {endpoint}")


def sanitize_existing_evidence(rows):
    """Rewrite persisted V1 /fixtures/players rows to strict V2 role semantics.

    Minutes and appearance are retained/recomputed from direct numeric minutes.
    Official starter/substitute LISTING remains false unless it came from the
    lineup endpoint. A provider substitute=True plus positive minutes may prove
    substitute appearance, but substitute=False never proves a starter.
    """
    out = []
    rewritten = 0
    for original in rows:
        row = dict(original)
        if sval(row, "capture_endpoint") == "/fixtures/players":
            minutes = as_int(row.get("minutes"))
            appearance = minutes is not None and minutes > 0
            substitute = sval(row, "provider_substitute_flag").lower() == "true"
            sub_appearance = appearance and substitute
            desired = {
                "appearance_confirmed": "true" if appearance else "false",
                "minutes_confirmed": "true" if minutes is not None and minutes >= 0 else "false",
                "starter_listed_confirmed": "false",
                "substitute_listed_confirmed": "false",
                "substitute_appearance_confirmed": "true" if sub_appearance else "false",
                "lineup_role": (
                    "SUBSTITUTE_APPEARANCE_PROVIDER_FLAG"
                    if sub_appearance else
                    ("APPEARANCE_ROLE_UNVERIFIED" if appearance
                     else "PLAYER_STATS_LISTED_NO_APPEARANCE")
                ),
            }
            if any(sval(row, key) != value for key, value in desired.items()):
                rewritten += 1
                row.update(desired)
        out.append(row)
    return out, rewritten


def merge_evidence(existing, incoming):
    merged = {
        evidence_key(row): dict(row)
        for row in existing
        if all(evidence_key(row))
    }
    for row in incoming:
        key = evidence_key(row)
        if not all(key):
            continue
        old = merged.get(key)
        if old and (
            sval(old, "capture_endpoint") != sval(row, "capture_endpoint")
            or sval(old, "evidence_tier") != sval(row, "evidence_tier")
        ):
            raise ValueError(
                f"evidence contract conflict for {key}: "
                f"{sval(old,'capture_endpoint')}/{sval(old,'evidence_tier')} vs "
                f"{sval(row,'capture_endpoint')}/{sval(row,'evidence_tier')}"
            )
        merged[key] = dict(row)
    return [merged[key] for key in sorted(merged)]


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def attempt_count(row):
    try:
        return max(0, int(sval(row, "attempt_count") or "0"))
    except ValueError:
        return 0


def retry_cooldown_hours(row):
    result = sval(row, "last_attempt_result").upper()
    attempts = attempt_count(row)
    if attempts <= 0:
        return 0.0
    if result == "NO_DATA":
        return min(168.0, 24.0 * (2 ** max(0, attempts - 1)))
    if result == "ERROR":
        return min(24.0, 1.0 * (2 ** max(0, attempts - 1)))
    return 0.0


def retry_ready(row, now):
    last = parse_dt(row.get("last_attempt_at_utc"))
    if last is None:
        return True
    cooldown = retry_cooldown_hours(row)
    return cooldown <= 0 or now >= last + timedelta(hours=cooldown)


def capture_cell_key(row):
    return (
        sval(row, "provider_league_id"),
        sval(row, "season"),
        sval(row, "capture_endpoint"),
    )


def observed_cell_yield(backlog):
    stats = {}
    for row in backlog:
        key = capture_cell_key(row)
        item = stats.setdefault(key, {"attempted": 0, "captured": 0})
        if attempt_count(row) > 0:
            item["attempted"] += 1
            if sval(row, "backlog_status") == "CAPTURED":
                item["captured"] += 1
    for item in stats.values():
        attempted = item["attempted"]
        captured = item["captured"]
        item["yield_rate"] = captured / attempted if attempted else None
        if captured > 0:
            item["class"] = "PROVEN_POSITIVE"
        elif attempted >= 3:
            item["class"] = "LOW_YIELD"
        else:
            item["class"] = "UNPROVEN"
    return stats


def candidate_rows(backlog, now, limit, lineup_exploration=0):
    eligible = [
        row for row in backlog
        if sval(row, "backlog_status") != "CAPTURED"
        and retry_ready(row, now)
    ]
    cell_stats = observed_cell_yield(backlog)
    class_rank = {"PROVEN_POSITIVE": 0, "UNPROVEN": 1, "LOW_YIELD": 2}

    def key(row):
        last = parse_dt(row.get("last_attempt_at_utc"))
        kickoff = parse_dt(row.get("kickoff_utc"))
        recent_first = -(kickoff.timestamp()) if kickoff is not None else float("inf")
        try:
            priority = int(sval(row, "capture_priority") or "99")
        except ValueError:
            priority = 99

        cell = cell_stats.get(
            capture_cell_key(row),
            {"attempted": 0, "captured": 0, "yield_rate": None, "class": "UNPROVEN"},
        )
        bucket = class_rank[cell["class"]]
        observed_yield = cell["yield_rate"] if cell["yield_rate"] is not None else -1.0
        if last is None:
            retry_rank = 0
            retry_time = 0.0
        else:
            retry_rank = 1
            retry_time = last.timestamp()
        return (
            bucket,
            priority,
            -observed_yield,
            retry_rank,
            retry_time,
            recent_first,
            sval(row, "fixture_id"),
        )

    eligible.sort(key=key)
    limit = max(0, int(limit))
    lineup_exploration = max(0, min(int(lineup_exploration), limit))

    # Reserve a small deterministic exploration slice for historical lineups so
    # DIRECT_MINUTES coverage cannot starve the squad-only contour forever.
    lineup_pool = [
        row for row in eligible if sval(row, "capture_endpoint") == "/fixtures/lineups"
    ]
    lineup_pool.sort(key=key)
    selected = lineup_pool[:lineup_exploration]
    selected_ids = {sval(row, "fixture_id") for row in selected}

    remaining = [row for row in eligible if sval(row, "fixture_id") not in selected_ids]
    remaining.sort(key=key)
    selected.extend(remaining[: max(0, limit - len(selected))])
    return selected[:limit]


def cell_yield_summary(backlog):
    stats = observed_cell_yield(backlog)
    classes = Counter(item["class"] for item in stats.values())
    by_endpoint = {}
    for key, item in stats.items():
        endpoint = key[2]
        bucket = by_endpoint.setdefault(endpoint, Counter())
        bucket[item["class"]] += 1
    return {
        "cell_class_counts": dict(sorted(classes.items())),
        "cell_class_counts_by_endpoint": {
            endpoint: dict(sorted(counts.items()))
            for endpoint, counts in sorted(by_endpoint.items())
        },
    }


def validate_backlog_meta(meta, backlog):
    return bool(
        meta
        and not meta.get("_invalid_json")
        and meta.get("version") == "PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_EVIDENCE_BACKLOG_V1"
        and meta.get("status") == "OK"
        and int(meta.get("backlog_rows") or 0) == len(backlog)
        and int(meta.get("configured_windows") or 0) == 39
        and int(meta.get("duplicate_backlog_fixture_ids") or 0) == 0
        and int(meta.get("invalid_backlog_rows") or 0) == 0
        and meta.get("final_tournaments_included") is False
        and meta.get("outside_fixed_window_fixtures_queued") is False
        and meta.get("appearance_inference_allowed") is False
        and int(meta.get("provider_calls") or 0) == 0
        and meta.get("research_only") is True
        and meta.get("operational_betting_authority") is False
    )


def protected_calls():
    return max(0, int(os.getenv("STAGE80_INTL_DUTY_PLAYER_EVIDENCE_PROTECTED_CALLS", "512")))


def run(
    backlog_path=BACKLOG,
    backlog_meta_path=BACKLOG_META,
    evidence_path=EVIDENCE,
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
        else int(os.getenv("STAGE80_INTL_DUTY_PLAYER_EVIDENCE_MAX_API_CALLS", "10"))
    )

    backlog = read_csv(backlog_path)
    backlog_meta = read_json(backlog_meta_path)
    if not validate_backlog_meta(backlog_meta, backlog):
        raise ValueError("player-evidence backlog/meta contract is not ready")

    existing_evidence_raw = read_csv(evidence_path)
    existing_evidence, semantics_rewritten_rows = sanitize_existing_evidence(existing_evidence_raw)
    shared = audit.read(Path(shared_state_path))
    budget = audit.Budget(
        get,
        shared,
        now,
        limit=max_calls,
        daily_limit=int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "7000")),
        checkpoint=lambda state: audit.save(Path(shared_state_path), state),
        protected_calls=protected_calls(),
    )

    archive_stats = {"archive_read_hits": 0, "archive_read_misses": 0, "archive_read_errors": 0}
    historical_get = make_archive_before_budget_get(budget, archive_stats)
    calls_before = int(shared.get("api_day_calls") or 0)
    lineup_exploration_calls = min(
        max_calls,
        max(0, int(os.getenv("STAGE80_INTL_DUTY_LINEUP_EXPLORATION_CALLS", "0"))),
    )
    candidates = candidate_rows(
        backlog, now, max_calls, lineup_exploration=lineup_exploration_calls
    )
    evidence = existing_evidence
    warnings = []
    attempts = []

    by_fixture = {sval(row, "fixture_id"): row for row in backlog}

    for row in candidates:
        fixture_id = sval(row, "fixture_id")
        endpoint = sval(row, "capture_endpoint")
        attempted_at = iso_now(now)
        result = ""
        error = ""
        try:
            payload = historical_get(
                endpoint,
                {"fixture": fixture_id},
                ttl_seconds=365 * 24 * 3600,
                force_refresh=False,
            )
            incoming = normalize_payload(payload, row, attempted_at)
            if not incoming:
                result = "NO_DATA"
                warnings.append(f"{fixture_id}: provider returned no usable {endpoint} rows")
            else:
                evidence = merge_evidence(evidence, incoming)
                result = "CAPTURED"
        except audit.ProtectedBudgetError as exc:
            warnings.append(str(exc))
            break
        except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            result = "ERROR"
            error = str(exc)
            warnings.append(f"{fixture_id}: {exc}")

        if not result:
            continue

        current = by_fixture[fixture_id]
        current["attempt_count"] = str(attempt_count(current) + 1)
        current["last_attempt_at_utc"] = attempted_at
        current["last_attempt_result"] = result
        current["last_error"] = error
        if result == "CAPTURED":
            current["backlog_status"] = "CAPTURED"
            current["captured_at_utc"] = attempted_at
        elif result == "NO_DATA":
            current["backlog_status"] = "NO_DATA"
        else:
            current["backlog_status"] = "ERROR"

        attempts.append({
            "fixture_id": fixture_id,
            "endpoint": endpoint,
            "result": result,
        })
        write_csv(backlog_path, queue.FIELDS, backlog)
        write_csv(evidence_path, EVIDENCE_FIELDS, evidence)

    write_csv(backlog_path, queue.FIELDS, backlog)
    write_csv(evidence_path, EVIDENCE_FIELDS, evidence)
    audit.save(Path(shared_state_path), shared)

    status_counts = Counter(sval(row, "backlog_status") for row in backlog)
    evidence_ids = [evidence_key(row) for row in evidence if all(evidence_key(row))]
    duplicate_evidence_rows = len(evidence_ids) - len(set(evidence_ids))
    invalid_evidence_rows = sum(
        not (
            all(evidence_key(row))
            and sval(row, "capture_endpoint") in {"/fixtures/players", "/fixtures/lineups"}
            and sval(row, "matchday_squad_confirmed") == "true"
            and sval(row, "formal_callup_status") == "NOT_SEPARATELY_VERIFIED"
            and sval(row, "travel_status") == "NOT_DERIVED"
            and sval(row, "nationality_inference_allowed") == "false"
            and sval(row, "travel_inference_allowed") == "false"
            and sval(row, "research_only") == "true"
            and sval(row, "operational_betting_authority") == "false"
            and sval(row, "creates_signal") == "false"
        )
        for row in evidence
    )

    broker_stats = get_broker().stats() if get is api_get else {}
    if int(broker_stats.get("archive_errors") or 0) > 0:
        warnings.append(f"raw archive write failures: {broker_stats.get('archive_errors')}")
    attempted_results = Counter(item["result"] for item in attempts)
    candidate_endpoint_counts = Counter(
        sval(row, "capture_endpoint") for row in candidates
    )
    yield_summary = cell_yield_summary(backlog)

    captured_fixture_ids = {
        sval(row, "fixture_id")
        for row in backlog
        if sval(row, "backlog_status") == "CAPTURED"
    }

    meta = {
        "version": VERSION,
        "generated_at_utc": iso_now(now),
        "status": "OK" if len(captured_fixture_ids) == len(backlog) else "COLLECTING",
        "backlog_rows": len(backlog),
        "backlog_status_counts": dict(sorted(status_counts.items())),
        "candidate_fixtures_this_run": len(candidates),
        "attempted_fixtures_this_run": len(attempts),
        "attempt_result_counts": dict(sorted(attempted_results.items())),
        "captured_fixtures_total": len(captured_fixture_ids),
        "pending_or_retry_fixtures": len(backlog) - len(captured_fixture_ids),
        "evidence_rows": len(evidence),
        "existing_evidence_semantics_rewritten_rows": semantics_rewritten_rows,
        "candidate_order": "LINEUP_EXPLORATION_THEN_CELL_YIELD_CLASS_THEN_TIER_THEN_RECENCY",
        "candidate_policy": "PROVEN_POSITIVE_THEN_UNPROVEN_THEN_LOW_YIELD",
        "lineup_exploration_calls_requested": lineup_exploration_calls,
        "candidate_endpoint_counts": dict(sorted(candidate_endpoint_counts.items())),
        "observed_cell_yield": yield_summary,
        "player_stats_starter_inference_allowed": False,
        "player_stats_substitute_listing_inference_allowed": False,
        "unique_evidence_keys": len(set(evidence_ids)),
        "duplicate_evidence_rows": duplicate_evidence_rows,
        "invalid_evidence_rows": invalid_evidence_rows,
        "evidence_fixture_count": len({
            sval(row, "fixture_id") for row in evidence if sval(row, "fixture_id")
        }),
        "evidence_player_count": len({
            sval(row, "player_id") for row in evidence if sval(row, "player_id")
        }),
        "matchday_squad_confirmed_rows": sum(
            sval(row, "matchday_squad_confirmed") == "true" for row in evidence
        ),
        "appearance_confirmed_rows": sum(
            sval(row, "appearance_confirmed") == "true" for row in evidence
        ),
        "minutes_confirmed_rows": sum(
            sval(row, "minutes_confirmed") == "true" for row in evidence
        ),
        "starter_listed_confirmed_rows": sum(
            sval(row, "starter_listed_confirmed") == "true" for row in evidence
        ),
        "substitute_listed_confirmed_rows": sum(
            sval(row, "substitute_listed_confirmed") == "true" for row in evidence
        ),
        "substitute_appearance_confirmed_rows": sum(
            sval(row, "substitute_appearance_confirmed") == "true" for row in evidence
        ),
        "formal_callup_rows_confirmed": 0,
        "travel_rows_derived": 0,
        "provider_budget_calls": budget.calls,
        "archive_first_enabled": True,
        "archive_read_hits": archive_stats["archive_read_hits"],
        "archive_read_misses": archive_stats["archive_read_misses"],
        "archive_read_errors": archive_stats["archive_read_errors"],
        "real_api_calls": broker_stats.get("real_api_calls"),
        "provider_successes": broker_stats.get("provider_successes"),
        "archive_write_successes": broker_stats.get("archive_write_successes"),
        "archive_write_failures": broker_stats.get("archive_errors"),
        "provider_archive_write_through_ok": (broker_stats.get("provider_successes") == (broker_stats.get("archive_write_successes") or 0) + (broker_stats.get("archive_errors") or 0)) if broker_stats else None,
        "daily_api_calls_before": calls_before,
        "daily_api_calls_after": int(shared.get("api_day_calls") or 0),
        "protected_calls": protected_calls(),
        "raw_archive_enabled": broker_stats.get("archive_enabled"),
        "raw_archive_backend": broker_stats.get("archive_backend"),
        "raw_archive_observations": broker_stats.get("archive_observations"),
        "raw_archive_errors": broker_stats.get("archive_errors"),
        "warnings": warnings,
        "nationality_inference_allowed": False,
        "travel_inference_allowed": False,
        "formal_callup_separately_verified": False,
        "lineup_listing_implies_appearance": False,
        "player_stats_substitute_true_can_confirm_substitute_appearance": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "next_stage": (
            "Provider-free join of direct international player evidence to PBK API-Football player IDs, "
            "then derive strictly historical pre-match duty/load features."
        ),
    }
    write_json(meta_path, meta)
    return meta


def main():
    print(json.dumps(run(), ensure_ascii=False))


if __name__ == "__main__":
    main()
