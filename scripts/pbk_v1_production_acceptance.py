#!/usr/bin/env python3
"""Provider-free PBK v1 production acceptance gate.

This gate does not call API-Football or any network endpoint. It evaluates only
operational evidence already captured by production jobs plus the disposable
Stage72 SQLite read model. A PASS is latched once earned unless a hard integrity
failure is observed later; temporary absence of candidates or later budget
pressure must not erase previously proven production behaviour.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

VERSION = "PBK_V1_PRODUCTION_ACCEPTANCE_V1"
OPS = Path(os.getenv("OPS_DIR", "ops"))
DB = Path(os.getenv("STAGE72_DB_PATH", "build/pbk_unified.sqlite"))
OUT_JSON = OPS / "pbk_v1_production_acceptance.json"
OUT_MD = OPS / "pbk_v1_production_acceptance.md"

LIVE_FIELDS = {
    "fixture_id", "source_status", "status", "score_home", "score_away",
    "elapsed", "observed_at_utc", "live_observed_at_utc",
    "live_freshness_status", "red_cards_home", "red_cards_away",
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dt(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_csv(path):
    if not path.exists():
        return [], []
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            return list(reader.fieldnames or []), list(reader)
    except (OSError, UnicodeError, csv.Error):
        return [], []


def integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def check(code, status, message, evidence=None):
    return {
        "code": code,
        "status": status,
        "message": message,
        "evidence": evidence or {},
    }


def combine(checks):
    statuses = [item["status"] for item in checks]
    if "FAIL" in statuses:
        return "FAIL"
    if statuses and all(value == "PASS" for value in statuses):
        return "PASS"
    return "WAITING"


def current_round_check(ops):
    meta = read_json(ops / "current_round_last_run.json")
    if not meta:
        return [check("CURRENT_ROUND_PRESENT", "WAITING", "current-round metadata not published yet")]
    served_leagues = integer(meta.get("served_available_leagues", meta.get("available_leagues")))
    served_rows = integer(meta.get("served_fixture_rows", meta.get("fixture_rows")))
    serving = "PASS" if served_leagues > 0 and served_rows > 0 else "FAIL"
    checks = [check(
        "CURRENT_ROUND_SERVING", serving,
        "current round remains populated" if serving == "PASS" else "current round is empty",
        {"served_available_leagues": served_leagues, "served_fixture_rows": served_rows,
         "last_good_preserved": bool(meta.get("last_good_preserved"))},
    )]
    api_calls = integer(meta.get("api_calls"))
    refreshed = integer(meta.get("refreshed_leagues"))
    exhausted = bool(meta.get("budget_exhausted"))
    if api_calls > 0 and refreshed > 0 and not exhausted:
        status = "PASS"
        message = "real provider-backed current-round refresh observed"
    else:
        status = "WAITING"
        message = "waiting for a provider-backed current-round refresh after budget reset"
    checks.append(check(
        "CURRENT_ROUND_PROVIDER_REFRESH", status, message,
        {"run_at_utc": meta.get("run_at_utc"), "api_calls": api_calls,
         "refreshed_leagues": refreshed, "budget_exhausted": exhausted,
         "refresh_status": meta.get("refresh_status")},
    ))
    if exhausted and (served_leagues <= 0 or served_rows <= 0 or not meta.get("last_good_preserved")):
        checks.append(check(
            "CURRENT_ROUND_BUDGET_SAFETY", "FAIL",
            "budget exhaustion destroyed or failed to preserve the last-good current round",
            {"last_good_preserved": bool(meta.get("last_good_preserved")),
             "served_fixture_rows": served_rows},
        ))
    else:
        checks.append(check(
            "CURRENT_ROUND_BUDGET_SAFETY", "PASS",
            "budget pressure is non-destructive",
            {"budget_exhausted": exhausted, "last_good_preserved": bool(meta.get("last_good_preserved"))},
        ))
    return checks


def live_checks(ops):
    meta = read_json(ops / "live_fixture_overlay_last_run.json")
    fields, rows = read_csv(ops / "live_fixture_overlay.csv")
    checks = []
    if not meta:
        checks.append(check("LIVE_PROVIDER_OBSERVATION", "WAITING", "LIVE observation metadata not published yet"))
    else:
        candidates = integer(meta.get("candidate_fixtures"))
        calls = integer(meta.get("provider_calls"))
        updated = integer(meta.get("updated_fixtures"))
        exhausted = bool(meta.get("budget_exhausted"))
        if candidates > 0 and calls > 0 and updated > 0 and not exhausted:
            status = "PASS"
            message = "real LIVE provider batch observed"
        else:
            status = "WAITING"
            message = "waiting for a LIVE candidate batch with available provider budget"
        checks.append(check(
            "LIVE_PROVIDER_OBSERVATION", status, message,
            {"observed_at_utc": meta.get("observed_at_utc"), "candidate_fixtures": candidates,
             "provider_calls": calls, "updated_fixtures": updated, "budget_exhausted": exhausted,
             "status": meta.get("status")},
        ))
    missing = sorted(LIVE_FIELDS - set(fields))
    observed_rows = [row for row in rows if row.get("live_observed_at_utc")]
    if missing:
        contract_status = "FAIL"
        contract_message = "LIVE overlay contract is missing required fields"
    elif observed_rows:
        contract_status = "PASS"
        contract_message = "LIVE overlay carries score/status/freshness/red-card fields"
    else:
        contract_status = "WAITING"
        contract_message = "LIVE overlay schema is ready; waiting for a real observed row"
    checks.append(check(
        "LIVE_OVERLAY_CONTRACT", contract_status, contract_message,
        {"rows": len(rows), "observed_rows": len(observed_rows), "missing_fields": missing},
    ))
    return checks, meta


def stage_propagation_check(ops, live_meta):
    stage72 = read_json(ops / "stage72_last_run.json") or {}
    stage73 = read_json(ops / "stage73_last_run.json") or {}
    live_at = dt((live_meta or {}).get("observed_at_utc"))
    s72_at = dt(stage72.get("run_at_utc"))
    s73_at = dt(stage73.get("run_at_utc"))
    base_ok = (
        stage72.get("status") == "OK"
        and stage72.get("integrity_check") == "ok"
        and stage73.get("status") == "OK"
        and integer(stage73.get("passed")) == integer(stage73.get("total"))
        and integer(stage73.get("total")) > 0
    )
    real_live = live_meta and integer(live_meta.get("provider_calls")) > 0 and integer(live_meta.get("updated_fixtures")) > 0
    if not base_ok:
        status = "FAIL"
        message = "Stage72/Stage73 integrity or API self-tests are not healthy"
    elif not real_live:
        status = "WAITING"
        message = "data layer is healthy; waiting for real LIVE evidence to propagate"
    elif live_at and s72_at and s73_at and s72_at >= live_at and s73_at >= s72_at:
        status = "PASS"
        message = "real LIVE observation propagated through Stage72 and Stage73"
    else:
        status = "WAITING"
        message = "LIVE observation exists; waiting for downstream Stage72/Stage73 rebuild"
    return check(
        "LIVE_STAGE72_STAGE73_PROPAGATION", status, message,
        {"live_observed_at_utc": (live_meta or {}).get("observed_at_utc"),
         "stage72_run_at_utc": stage72.get("run_at_utc"), "stage72_status": stage72.get("status"),
         "stage73_run_at_utc": stage73.get("run_at_utc"), "stage73_status": stage73.get("status"),
         "stage73_passed": stage73.get("passed"), "stage73_total": stage73.get("total")},
    )


def valid_standings_evidence(ops):
    fields, rows = read_csv(ops / "standings_snapshots.csv")
    fixtures_fields, fixtures = read_csv(ops / "current_round_fixtures.csv")
    required = {"snapshot_id", "provider_league_id", "season", "observed_at_utc", "team_id", "source"}
    missing = sorted(required - set(fields))
    if missing:
        return [], [], missing
    groups = {}
    for row in rows:
        sid = str(row.get("snapshot_id") or "").strip()
        if sid:
            groups.setdefault(sid, []).append(row)
    valid_groups = []
    prematch_groups = []
    for sid, items in groups.items():
        league_season = {(str(x.get("provider_league_id") or ""), str(x.get("season") or "")) for x in items}
        observed = {str(x.get("observed_at_utc") or "") for x in items}
        teams = [str(x.get("team_id") or "") for x in items]
        sources = {str(x.get("source") or "") for x in items}
        if len(league_season) != 1 or len(observed) != 1 or not all(teams) or len(teams) != len(set(teams)):
            continue
        observed_at = dt(next(iter(observed)))
        if observed_at is None or "api-football:/standings" not in sources:
            continue
        valid_groups.append((sid, items, observed_at, next(iter(league_season))))
        league, season = next(iter(league_season))
        candidates = []
        for fixture in fixtures:
            if str(fixture.get("provider_league_id") or "") != league or str(fixture.get("season") or "") != season:
                continue
            kickoff = dt(fixture.get("kickoff_utc"))
            if kickoff and observed_at <= kickoff and (kickoff - observed_at).total_seconds() <= 90 * 60:
                candidates.append(fixture)
        if candidates:
            prematch_groups.append((sid, items, observed_at, candidates))
    return valid_groups, prematch_groups, missing


def motivation_db_check(db):
    if not db.exists():
        return check("MOTIVATION_READ_MODEL", "WAITING", "Stage72 SQLite read model not available in this run")
    try:
        conn = sqlite3.connect(db)
        try:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='fixture_motivation'"
            ).fetchone()
            if not table:
                return check("MOTIVATION_READ_MODEL", "FAIL", "fixture_motivation table is missing")
            total = integer(conn.execute("SELECT COUNT(*) FROM fixture_motivation").fetchone()[0])
            available = integer(conn.execute(
                "SELECT COUNT(*) FROM fixture_motivation WHERE available='1' AND no_lookahead='1'"
            ).fetchone()[0])
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return check("MOTIVATION_READ_MODEL", "FAIL", "cannot inspect fixture_motivation", {"error": str(exc)})
    if available > 0:
        status = "PASS"
        message = "at least one real no-lookahead motivation projection is available"
    else:
        status = "WAITING"
        message = "motivation projection exists; waiting for captured standings evidence"
    return check("MOTIVATION_READ_MODEL", status, message, {"rows": total, "available_no_lookahead_rows": available})


def standings_checks(ops, db):
    valid, prematch, missing = valid_standings_evidence(ops)
    checks = []
    if missing:
        status = "WAITING" if not (ops / "standings_snapshots.csv").exists() else "FAIL"
        message = "standings snapshot ledger not captured yet" if status == "WAITING" else "standings ledger schema is incomplete"
    elif valid:
        status = "PASS"
        message = "real provider standings snapshot exists"
    else:
        status = "WAITING"
        message = "waiting for first valid provider standings snapshot"
    checks.append(check(
        "STANDINGS_PROVIDER_SNAPSHOT", status, message,
        {"valid_snapshots": len(valid), "rows": sum(len(group[1]) for group in valid), "missing_fields": missing},
    ))
    if valid and not prematch:
        no_lookahead_status = "FAIL"
        no_lookahead_message = "standings snapshots exist but no snapshot can be tied to a <=90m pre-kickoff fixture"
    elif prematch:
        no_lookahead_status = "PASS"
        no_lookahead_message = "provider standings evidence is tied to a pre-kickoff cutoff"
    else:
        no_lookahead_status = "WAITING"
        no_lookahead_message = "waiting for pre-kickoff standings evidence"
    checks.append(check(
        "STANDINGS_NO_LOOKAHEAD_EVIDENCE", no_lookahead_status, no_lookahead_message,
        {"prematch_snapshots": len(prematch)},
    ))
    stage72 = read_json(ops / "stage72_last_run.json") or {}
    stable = stage72.get("stable_counts") if isinstance(stage72.get("stable_counts"), dict) else {}
    standings_count = integer(stable.get("standings_snapshots"))
    leakage = integer(stage72.get("historical_leakage_violations"))
    if leakage > 0:
        layer_status = "FAIL"
        layer_message = "Stage72 detected historical standings leakage"
    elif standings_count > 0:
        layer_status = "PASS"
        layer_message = "Stage72 ingested real standings without leakage"
    else:
        layer_status = "WAITING"
        layer_message = "Stage72 is healthy but has not ingested standings yet"
    checks.append(check(
        "STAGE72_STANDINGS_INGESTION", layer_status, layer_message,
        {"stage72_status": stage72.get("status"), "standings_snapshots": standings_count,
         "historical_leakage_violations": leakage},
    ))
    checks.append(motivation_db_check(db))
    return checks


def global_checks(ops):
    health = read_json(ops / "system_health.json") or {}
    stage72 = read_json(ops / "stage72_last_run.json") or {}
    stage73 = read_json(ops / "stage73_last_run.json") or {}
    critical = integer((health.get("summary") or {}).get("critical_issues"))
    checks = [check(
        "SYSTEM_HEALTH_NO_CRITICAL", "PASS" if critical == 0 else "FAIL",
        "no CRITICAL system-health issues" if critical == 0 else "system health contains CRITICAL issues",
        {"health_status": health.get("status"), "critical_issues": critical,
         "warnings": integer((health.get("summary") or {}).get("warnings"))},
    )]
    data_ok = stage72.get("status") == "OK" and stage72.get("integrity_check") == "ok"
    checks.append(check(
        "DATA_LAYER_INTEGRITY", "PASS" if data_ok else "FAIL",
        "Stage72 integrity is OK" if data_ok else "Stage72 integrity is not OK",
        {"status": stage72.get("status"), "integrity_check": stage72.get("integrity_check"),
         "schema_version": stage72.get("schema_version")},
    ))
    api_ok = stage73.get("status") == "OK" and integer(stage73.get("total")) > 0 and integer(stage73.get("passed")) == integer(stage73.get("total"))
    checks.append(check(
        "INTERNAL_API_SELF_TEST", "PASS" if api_ok else "FAIL",
        "Stage73 self-tests pass" if api_ok else "Stage73 self-tests are not fully passing",
        {"status": stage73.get("status"), "passed": stage73.get("passed"), "total": stage73.get("total")},
    ))
    return checks


def latch(previous, key, current):
    old = (((previous or {}).get("items") or {}).get(key) or {})
    if old.get("status") == "PASS" and current.get("status") == "WAITING":
        preserved = dict(old)
        preserved["latched"] = True
        return preserved
    return current


def canonical_payload(ops=OPS, db=DB, previous=None):
    round_checks = current_round_check(ops)
    live, live_meta = live_checks(ops)
    item4_checks = round_checks + live + [stage_propagation_check(ops, live_meta)]
    item4 = {"status": combine(item4_checks), "checks": item4_checks}
    item5_checks = standings_checks(ops, db)
    item5 = {"status": combine(item5_checks), "checks": item5_checks}
    item4 = latch(previous, "4_today_live", item4)
    item5 = latch(previous, "5_standings_motivation", item5)
    globals_ = global_checks(ops)
    global_status = combine(globals_)
    statuses = [item4["status"], item5["status"], global_status]
    overall = "FAIL" if "FAIL" in statuses else ("PASS" if all(value == "PASS" for value in statuses) else "WAITING")
    next_actions = []
    if item4["status"] != "PASS":
        next_actions.append("Wait for post-reset current-round and LIVE candidate provider observations.")
    if item5["status"] != "PASS":
        next_actions.append("Wait for a <=75m pre-kickoff standings capture and downstream Stage72 motivation rebuild.")
    if global_status == "FAIL":
        next_actions.append("Resolve hard health/data-layer/API integrity failures before closure.")
    if overall == "PASS":
        next_actions.append("Production acceptance is complete; PBK v1 may proceed to final closure bookkeeping.")
    return {
        "version": VERSION,
        "status": overall,
        "ready_to_close": overall == "PASS",
        "provider_calls": 0,
        "network_calls": 0,
        "items": {"4_today_live": item4, "5_standings_motivation": item5},
        "global": {"status": global_status, "checks": globals_},
        "next_actions": next_actions,
    }


def fingerprint(payload):
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def render_markdown(payload):
    marks = {"PASS": "✅", "WAITING": "🟡", "FAIL": "❌"}
    lines = [
        "# PBK v1 Production Acceptance",
        "",
        f"Overall: **{marks.get(payload['status'], '•')} {payload['status']}**",
        "",
        "Provider/network calls by this gate: **0**.",
        "",
    ]
    for key, title in (("4_today_live", "Roadmap 4 — Today/LIVE"), ("5_standings_motivation", "Roadmap 5 — Standings/Motivation")):
        item = payload["items"][key]
        lines += [f"## {title}", "", f"Status: **{marks.get(item['status'], '•')} {item['status']}**", ""]
        for entry in item.get("checks", []):
            lines.append(f"- {marks.get(entry['status'], '•')} `{entry['code']}` — {entry['message']}")
        lines.append("")
    lines += ["## Global closure gate", ""]
    for entry in payload["global"]["checks"]:
        lines.append(f"- {marks.get(entry['status'], '•')} `{entry['code']}` — {entry['message']}")
    lines += ["", "## Next", ""]
    lines.extend(f"- {text}" for text in payload.get("next_actions", []))
    lines.append("")
    return "\n".join(lines)


def write_outputs(ops=OPS, db=DB):
    ops = Path(ops)
    db = Path(db)
    out_json = ops / OUT_JSON.name
    out_md = ops / OUT_MD.name
    previous = read_json(out_json)
    payload = canonical_payload(ops, db, previous=previous)
    state_fingerprint = fingerprint(payload)
    if previous and previous.get("state_fingerprint") == state_fingerprint:
        return previous, False
    payload["evaluated_at_utc"] = now_iso()
    payload["state_fingerprint"] = state_fingerprint
    ops.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(payload), encoding="utf-8")
    return payload, True


def main():
    payload, changed = write_outputs()
    print(json.dumps({
        "status": payload.get("status"), "ready_to_close": payload.get("ready_to_close"),
        "changed": changed, "provider_calls": 0, "network_calls": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
