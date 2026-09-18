#!/usr/bin/env python3
"""Provider-free PBK v1 final closure readiness gate.

This is the last *evidence* gate, not an automatic release/closure action.  It
combines the production acceptance result with real prospective performance
telemetry and static architecture/hygiene invariants.  No profitability target
is imposed: PBK v1 can be technically ready even when the tiny forward sample
is negative.  The point is to prove that real, prospective measurement exists
and remains separated from research WATCH data.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION = "PBK_V1_CLOSURE_READINESS_V1"
ROOT = Path(os.getenv("PBK_ROOT", "."))
OPS = Path(os.getenv("OPS_DIR", ROOT / "ops"))
OUT_JSON = OPS / "pbk_v1_closure_readiness.json"
OUT_MD = OPS / "pbk_v1_closure_readiness.md"

REQUIRED_FILES = [
    "scripts/pbk_calculation_contract.py",
    "scripts/pbk_forward_journal.py",
    "scripts/pbk_v1_production_acceptance.py",
    "scripts/stage76_disaster_recovery.py",
    "scripts/match_card_v2.py",
    "scripts/lineup_context.py",
    "scripts/lineup_surprise.py",
    "scripts/stage72_build_data_layer.py",
    "scripts/stage73_internal_api.py",
    "app/match-card.js",
    "app/today-live.js",
    "app/sw.js",
]

FORBIDDEN_FRONTEND_MARKERS = (
    "v3.football.api-sports.io",
    "x-apisports-key",
    "api_football_key",
    "/v1/match?fixture_id",
)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def check(code, status, message, evidence=None):
    return {"code": code, "status": status, "message": message, "evidence": evidence or {}}


def combine(checks):
    statuses = [item["status"] for item in checks]
    if "FAIL" in statuses:
        return "FAIL"
    if statuses and all(value == "PASS" for value in statuses):
        return "PASS"
    return "WAITING"


def production_acceptance_checks(ops: Path):
    payload = read_json(ops / "pbk_v1_production_acceptance.json")
    if not payload:
        return [check("PRODUCTION_ACCEPTANCE", "WAITING", "production acceptance state not published yet")]
    hard = bool(payload.get("hard_failure"))
    ready = bool(payload.get("ready_to_close"))
    status = "FAIL" if hard else ("PASS" if ready else "WAITING")
    message = (
        "production acceptance has a hard failure" if hard else
        "real Today/LIVE and standings/motivation production acceptance passed" if ready else
        "waiting for real provider-backed Today/LIVE and standings/motivation evidence"
    )
    return [check(
        "PRODUCTION_ACCEPTANCE", status, message,
        {
            "gate_status": payload.get("status"),
            "ready_to_close": ready,
            "hard_failure": hard,
            "roadmap_4_status": (payload.get("roadmap_4_today_live") or {}).get("status"),
            "roadmap_5_status": (payload.get("roadmap_5_standings_motivation") or {}).get("status"),
            "run_at_utc": payload.get("run_at_utc"),
        },
    )]


def performance_checks(ops: Path):
    forward = read_json(ops / "forward_performance.json")
    watch = read_json(ops / "watch_performance.json")
    checks = []
    if not forward:
        checks.append(check("CANONICAL_FORWARD_MEASUREMENT", "WAITING", "forward performance telemetry missing"))
    else:
        overall = forward.get("overall") if isinstance(forward.get("overall"), dict) else {}
        policy = forward.get("policy") if isinstance(forward.get("policy"), dict) else {}
        settled = integer(overall.get("settled_rows"))
        rows = integer(overall.get("rows"))
        coverage = number(overall.get("user_execution_coverage_pct"), -1)
        clean_scope = str(forward.get("scope") or "").strip().lower() == "clean prospective canonical forward only"
        no_backfill = str(policy.get("historical_backfill") or "").strip().lower() == "forbidden"
        okay = forward.get("status") == "OK" and clean_scope and no_backfill and rows > 0 and settled > 0 and coverage > 0
        checks.append(check(
            "CANONICAL_FORWARD_MEASUREMENT", "PASS" if okay else "WAITING",
            "real prospective canonical performance is being measured" if okay else "waiting for complete real prospective canonical performance evidence",
            {
                "status": forward.get("status"), "scope": forward.get("scope"), "rows": rows,
                "settled_rows": settled, "execution_coverage_pct": overall.get("user_execution_coverage_pct"),
                "roi_pct": overall.get("user_roi_pct"), "historical_backfill": policy.get("historical_backfill"),
                "profitability_required_for_closure": False,
            },
        ))
    if not watch:
        checks.append(check("WATCH_RESEARCH_MEASUREMENT", "WAITING", "WATCH performance telemetry missing"))
    else:
        overall = watch.get("overall") if isinstance(watch.get("overall"), dict) else {}
        policy = watch.get("policy") if isinstance(watch.get("policy"), dict) else {}
        crossings = integer(overall.get("crossings"))
        settled = integer(overall.get("settled"))
        research_scope = "watch" in str(watch.get("scope") or "").lower()
        canonical_unchanged = str(policy.get("canonical_forward") or "").strip().lower() == "unchanged"
        no_backfill = str(policy.get("historical_backfill") or "").strip().lower() == "forbidden"
        okay = watch.get("status") == "OK" and research_scope and canonical_unchanged and no_backfill and crossings > 0 and settled > 0
        checks.append(check(
            "WATCH_RESEARCH_MEASUREMENT", "PASS" if okay else "WAITING",
            "WATCH has separate real prospective research performance" if okay else "waiting for complete WATCH research performance evidence",
            {
                "status": watch.get("status"), "scope": watch.get("scope"), "crossings": crossings,
                "settled": settled, "roi_pct": overall.get("user_roi_pct"),
                "canonical_forward": policy.get("canonical_forward"), "historical_backfill": policy.get("historical_backfill"),
                "profitability_required_for_closure": False,
            },
        ))
    return checks


def static_hygiene_checks(root: Path):
    checks = []
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    checks.append(check(
        "REQUIRED_V1_MODULES", "PASS" if not missing else "FAIL",
        "all PBK v1 closure modules are present" if not missing else "required PBK v1 modules are missing",
        {"missing": missing},
    ))

    frontend_files = sorted((root / "app").glob("*.js"))
    violations = []
    for path in frontend_files:
        text = read_text(path).lower()
        for marker in FORBIDDEN_FRONTEND_MARKERS:
            if marker.lower() in text:
                violations.append(f"{path.relative_to(root)}:{marker}")
    checks.append(check(
        "FRONTEND_PROVIDER_ISOLATION", "PASS" if not violations else "FAIL",
        "frontend has no direct provider/legacy match endpoint" if not violations else "frontend contains forbidden provider or legacy endpoint markers",
        {"violations": violations, "files_scanned": len(frontend_files)},
    ))

    sw = read_text(root / "app/sw.js")
    pwa_ok = "pbk-shell-v15" in sw and "u.pathname.startsWith('/api/')" in sw and "cache:'no-store'" in sw
    checks.append(check(
        "PWA_API_NETWORK_ONLY", "PASS" if pwa_ok else "FAIL",
        "PWA shell is v15 and API traffic remains network-only/no-store" if pwa_ok else "PWA API cache invariant is missing",
        {"cache_v15": "pbk-shell-v15" in sw, "api_no_store": "cache:'no-store'" in sw},
    ))

    stage72 = read_text(root / "scripts/stage72_build_data_layer.py")
    match = re.search(r"SCHEMA_VERSION\s*=\s*['\"](\d+)['\"]", stage72)
    schema = integer(match.group(1)) if match else 0
    checks.append(check(
        "STAGE72_SCHEMA_BASELINE", "PASS" if schema >= 14 else "FAIL",
        "Stage72 schema is at or above the PBK v1 baseline" if schema >= 14 else "Stage72 schema regressed below PBK v1 baseline",
        {"schema_version": schema, "minimum": 14},
    ))

    stage73 = read_text(root / "scripts/stage73_internal_api.py")
    route_ok = "/v1/match-card" in stage73 and "/v1/rounds/current" in stage73 and "/v1/motivation" in stage73
    checks.append(check(
        "CORE_API_ROUTES", "PASS" if route_ok else "FAIL",
        "Today/LIVE, Match Card and motivation API routes are present" if route_ok else "one or more PBK v1 core API routes are missing",
        {},
    ))

    publisher_workflows = [
        ".github/workflows/stage75-probability-value.yml",
        ".github/workflows/standings-snapshot.yml",
        ".github/workflows/pbk-v1-production-acceptance.yml",
    ]
    unsafe = []
    for rel in publisher_workflows:
        text = read_text(root / rel)
        if "scripts/publish_operational_commit.py" not in text:
            unsafe.append(rel)
    checks.append(check(
        "CANONICAL_OPERATIONAL_PUBLISHER", "PASS" if not unsafe else "FAIL",
        "critical operational workflows use the canonical safe publisher" if not unsafe else "critical workflows bypass the canonical operational publisher",
        {"unsafe_workflows": unsafe},
    ))
    return checks


def render_markdown(payload):
    lines = [
        "# PBK v1 Closure Readiness",
        "",
        f"- Run: `{payload['run_at_utc']}`",
        f"- Status: **{payload['status']}**",
        f"- Ready for manual PBK v1 close: **{str(payload['ready_for_manual_close']).lower()}**",
        "- Profitability threshold: **not used for technical v1 closure**",
        "",
    ]
    for key, title in (
        ("production_acceptance", "Production acceptance"),
        ("real_performance", "Real prospective measurement"),
        ("static_hygiene", "Architecture / legacy / CI hygiene"),
    ):
        section = payload[key]
        lines.extend([f"## {title} — {section['status']}", ""])
        for item in section["checks"]:
            icon = "✅" if item["status"] == "PASS" else ("❌" if item["status"] == "FAIL" else "⏳")
            lines.append(f"- {icon} `{item['code']}` — {item['message']}")
        lines.append("")
    lines.append("PBK v1 must not be marked CLOSED automatically. A human closes it only after this file reports ready_for_manual_close=true.")
    return "\n".join(lines) + "\n"


def evaluate(root=ROOT, ops=OPS):
    production = production_acceptance_checks(ops)
    performance = performance_checks(ops)
    hygiene = static_hygiene_checks(root)
    sections = {
        "production_acceptance": {"checks": production, "status": combine(production)},
        "real_performance": {"checks": performance, "status": combine(performance)},
        "static_hygiene": {"checks": hygiene, "status": combine(hygiene)},
    }
    hard_failure = any(section["status"] == "FAIL" for section in sections.values())
    ready = all(section["status"] == "PASS" for section in sections.values())
    status = "FAIL" if hard_failure else ("READY" if ready else "WAITING")
    return {
        "version": VERSION,
        "run_at_utc": now_iso(),
        "status": status,
        "ready_for_manual_close": ready,
        "hard_failure": hard_failure,
        "production_acceptance": sections["production_acceptance"],
        "real_performance": sections["real_performance"],
        "static_hygiene": sections["static_hygiene"],
        "policy": {
            "provider_calls": 0,
            "profitability_threshold": None,
            "automatic_pbk_close": False,
            "historical_backfill": "forbidden",
        },
    }


def main():
    payload = evaluate()
    OPS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["hard_failure"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
