#!/usr/bin/env python3
"""Stage 67 — PBK system health and data-quality monitor.

Read-only operational QA over the existing ops layer. It makes no external API
calls, creates no betting signals, and never mutates canonical forward data.
"""
from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
OUT_JSON = OPS / "system_health.json"
OUT_MD = OPS / "system_health.md"
META = OPS / "stage67_last_run.json"

# Operational stages and maximum acceptable age in hours.
CHECKS = [
    ("Stage53 screener", "last_run.json", 30.0),
    ("Stage54 odds/closing", "stage54_last_run.json", 3.0),
    ("Stage55 context", "stage55_last_run.json", 3.0),
    ("Stage56 weather/XI", "stage56_last_run.json", 1.5),
    ("Stage57 international", "stage57_last_run.json", 30.0),
    ("Stage58 daily brief", "stage58_last_run.json", 3.0),
    ("Stage59 user execution", "stage59_last_run.json", 3.0),
    ("Stage60 forward performance", "stage60_last_run.json", 3.0),
    ("Stage61 EPL steam watch", "stage61_last_run.json", 2.0),
    ("Stage62 Bundesliga totals watch", "stage62_last_run.json", 2.0),
    ("Stage63 BTTS watch", "stage63_last_run.json", 2.0),
    ("Stage65 WATCH performance", "stage65_last_run.json", 3.0),
    ("Stage66 attention board", "stage66_last_run.json", 3.0),
]

REQUIRED_FILES = [
    "forward_log.csv",
    "user_forward_view.csv",
    "context_latest.csv",
    "daily_brief.md",
    "attention_board.md",
    "stage61_market_openers.csv",
    "stage62_ou_openers.csv",
    "stage63_btts_openers.csv",
]


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def fnum(v):
    try:
        x = float(str(v).strip())
        return x if math.isfinite(x) else None
    except Exception:
        return None


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def read_csv(path):
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def extract_run_time(d):
    if not isinstance(d, dict):
        return None
    for k in ("run_at_utc", "generated_at_utc", "screened_at_utc", "run_at", "generated_at", "updated_at_utc"):
        x = parse_dt(d.get(k))
        if x:
            return x
    return None


def add_issue(issues, severity, code, message):
    issues.append({"severity": severity, "code": code, "message": message})


def main():
    now = now_utc()
    issues = []
    stage_health = []

    for label, name, max_age_h in CHECKS:
        p = OPS / name
        if not p.exists():
            add_issue(issues, "CRITICAL", "MISSING_STAGE_META", f"{label}: missing {name}")
            stage_health.append({"stage": label, "file": name, "status": "MISSING", "age_h": None})
            continue
        d = read_json(p)
        if d is None:
            add_issue(issues, "CRITICAL", "INVALID_STAGE_META", f"{label}: unreadable JSON {name}")
            stage_health.append({"stage": label, "file": name, "status": "INVALID", "age_h": None})
            continue
        rt = extract_run_time(d)
        age_h = (now - rt).total_seconds() / 3600.0 if rt else None
        upstream_status = str(d.get("status") or "").upper()
        status = "OK"
        if upstream_status and upstream_status not in {"OK", "SUCCESS"}:
            status = "UPSTREAM_WARN"
            add_issue(issues, "WARN", "UPSTREAM_STATUS", f"{label}: upstream status={upstream_status}")
        if rt is None:
            status = "NO_TIMESTAMP"
            add_issue(issues, "WARN", "NO_RUN_TIMESTAMP", f"{label}: cannot determine run timestamp")
        elif age_h > max_age_h:
            sev = "CRITICAL" if age_h > max_age_h * 2 else "WARN"
            status = "STALE"
            add_issue(issues, sev, "STALE_STAGE", f"{label}: age {age_h:.2f}h > {max_age_h:.2f}h")
        stage_health.append({
            "stage": label, "file": name, "status": status,
            "run_at_utc": iso(rt) if rt else None,
            "age_h": round(age_h, 3) if age_h is not None else None,
            "max_age_h": max_age_h,
        })

    for name in REQUIRED_FILES:
        p = OPS / name
        if not p.exists() or p.stat().st_size == 0:
            add_issue(issues, "CRITICAL", "MISSING_REQUIRED_FILE", f"Missing/empty required ops file: {name}")

    forward = read_csv(OPS / "forward_log.csv")
    user = read_csv(OPS / "user_forward_view.csv")
    contexts = read_csv(OPS / "context_latest.csv")
    ctx_ids = {str(r.get("forward_id") or "") for r in contexts}

    # Canonical uniqueness.
    fids = [str(r.get("forward_id") or "") for r in forward if r.get("forward_id")]
    dup_fids = sorted({x for x in fids if fids.count(x) > 1})
    if dup_fids:
        add_issue(issues, "CRITICAL", "DUPLICATE_FORWARD_ID", f"Duplicate forward_id rows: {', '.join(dup_fids[:10])}")

    active = [r for r in user if str(r.get("status") or "").upper() in {"PAPER", "OPEN", "REVIEW"}]
    exec_missing = 0
    context_missing = 0
    malformed_active = 0
    for r in active:
        fid = str(r.get("forward_id") or "")
        if not fid or not r.get("api_fixture_id") or not parse_dt(r.get("kickoff_utc")):
            malformed_active += 1
        if str(r.get("user_execution_status") or "").upper() != "FROZEN" or fnum(r.get("paper_user_execution_odds")) is None:
            exec_missing += 1
        if fid and fid not in ctx_ids:
            context_missing += 1

    if malformed_active:
        add_issue(issues, "CRITICAL", "MALFORMED_ACTIVE_FORWARD", f"{malformed_active} active canonical rows lack identity/kickoff")
    if exec_missing:
        add_issue(issues, "WARN", "MISSING_USER_EXECUTION", f"{exec_missing}/{len(active)} active rows lack frozen executable Marathonbet paper price")
    if context_missing:
        add_issue(issues, "WARN", "MISSING_CONTEXT", f"{context_missing}/{len(active)} active rows lack context_latest row")

    # WATCH data integrity: watch_id must be unique in crossing ledgers.
    watch_specs = [
        ("Stage61", "stage61_market_crossings.csv"),
        ("Stage62", "stage62_ou_crossings.csv"),
        ("Stage63", "stage63_btts_crossings.csv"),
    ]
    watch_crossings = 0
    for label, name in watch_specs:
        rows = read_csv(OPS / name)
        watch_crossings += len(rows)
        ids = [str(r.get("watch_id") or "") for r in rows if r.get("watch_id")]
        if len(ids) != len(set(ids)):
            add_issue(issues, "CRITICAL", "DUPLICATE_WATCH_ID", f"{label}: duplicate watch_id in {name}")

    critical = sum(1 for x in issues if x["severity"] == "CRITICAL")
    warns = sum(1 for x in issues if x["severity"] == "WARN")
    overall = "CRITICAL" if critical else ("WARN" if warns else "HEALTHY")

    payload = {
        "generated_at_utc": iso(now),
        "status": overall,
        "summary": {
            "critical_issues": critical,
            "warnings": warns,
            "active_canonical_rows": len(active),
            "frozen_user_execution_rows": sum(1 for r in active if str(r.get("user_execution_status") or "").upper() == "FROZEN"),
            "active_rows_with_context": sum(1 for r in active if str(r.get("forward_id") or "") in ctx_ids),
            "watch_crossing_rows": watch_crossings,
        },
        "stage_health": stage_health,
        "issues": issues,
        "policy": {
            "external_api_calls": 0,
            "canonical_forward_mutation": "FORBIDDEN",
            "purpose": "detect stale/missing/corrupt operational data before it reaches the user-facing layer",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    icon = {"HEALTHY": "🟢", "WARN": "🟠", "CRITICAL": "🔴"}[overall]
    md = [
        "# PBK System Health",
        "",
        f"Обновлено UTC: {iso(now)}",
        f"Статус: {icon} **{overall}** | critical {critical} | warnings {warns}",
        "",
        "## Ключевые проверки",
        f"- Активные canonical: {len(active)}",
        f"- Frozen Marathonbet execution: {payload['summary']['frozen_user_execution_rows']}/{len(active)}",
        f"- Context coverage: {payload['summary']['active_rows_with_context']}/{len(active)}",
        f"- WATCH crossings накоплено: {watch_crossings}",
        "",
        "## Свежесть этапов",
    ]
    for x in stage_health:
        age = "N/A" if x["age_h"] is None else f"{x['age_h']:.2f}h"
        md.append(f"- {x['stage']}: **{x['status']}** | age {age} | limit {x['max_age_h']}h")
    md += ["", "## Проблемы"]
    if not issues:
        md.append("- Нет. Все проверяемые контуры выглядят согласованно.")
    else:
        for x in issues:
            md.append(f"- **{x['severity']}** `{x['code']}` — {x['message']}")
    md += [
        "",
        "> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    META.write_text(json.dumps({
        "run_at_utc": iso(now),
        "status": "OK",
        "system_health": overall,
        "critical_issues": critical,
        "warnings": warns,
        "active_canonical_rows": len(active),
        "watch_crossing_rows": watch_crossings,
        "api_calls": 0,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"system_health": overall, "critical": critical, "warnings": warns, "active": len(active)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
