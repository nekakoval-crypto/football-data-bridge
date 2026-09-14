#!/usr/bin/env python3
"""Reconcile Stage67 health with current Stage72 contracts.

Standings snapshots are an optional-yet-stable source until the first real
provider observation.  Stage72 deliberately creates an empty stable table when
that ledger does not exist, so its absence must not make the whole product
CRITICAL.  Schema validation is tied to the checked-in Stage72 schema manifest
instead of a historical hard-coded version.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

OPTIONAL_STABLE_SOURCES = {"standings_snapshots.csv"}
FALSE_MISSING_CODES = {"MISSING_STABLE_SOURCES", "STAGE72_MISSING_STABLE_SOURCE"}
SCHEMA_CODE = "SCHEMA_VERSION"


def read_json(path: Path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return fallback


def render_markdown(health: dict) -> str:
    status = str(health.get("status") or "UNKNOWN").upper()
    icon = {"HEALTHY": "🟢", "WARN": "🟠", "CRITICAL": "🔴"}.get(status, "⚪")
    summary = health.get("summary") or {}
    issues = health.get("issues") or []
    lines = [
        "# PBK System Health",
        "",
        f"Обновлено UTC: {health.get('generated_at_utc', '')}",
        f"Статус: {icon} **{status}** | critical {summary.get('critical_issues', 0)} | warnings {summary.get('warnings', 0)}",
        "",
        "## Ключевые проверки",
        f"- Stage72 Data Layer: integrity **{summary.get('stage72_integrity', 'N/A')}** | tables {summary.get('stage72_tables', 'N/A')} | schema v{summary.get('stage72_schema_version', 'N/A')}",
        f"- Stage73 Internal API: tests **{summary.get('stage73_api_tests', 'N/A')}** | API {summary.get('stage73_api_version', 'N/A')}",
    ]
    pending = summary.get("optional_stable_sources_pending") or []
    if pending:
        lines.append("- Optional stable sources pending: " + ", ".join(map(str, pending)))
    lines += ["", "## Свежесть этапов"]
    for row in health.get("stage_health") or []:
        age = "N/A" if row.get("age_h") is None else f"{float(row['age_h']):.2f}h"
        lines.append(
            f"- {row.get('stage')}: **{row.get('status')}** | age {age} | limit {row.get('max_age_h')}h"
        )
    lines += ["", "## Проблемы"]
    if issues:
        for issue in issues:
            lines.append(
                f"- **{issue.get('severity')}** `{issue.get('code')}` — {issue.get('message')}"
            )
    else:
        lines.append("- Нет. Все проверяемые контуры выглядят согласованно.")
    lines += [
        "",
        "> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.",
    ]
    return "\n".join(lines)


def reconcile(ops: Path) -> dict:
    health_path = ops / "system_health.json"
    health = read_json(health_path)
    if not isinstance(health, dict):
        raise RuntimeError("system_health.json is missing or invalid")

    stage72 = read_json(ops / "stage72_last_run.json", {}) or {}
    schema = read_json(ops / "stage72_schema.json", {}) or {}
    missing = [str(x) for x in (stage72.get("missing_stable_sources") or [])]
    required_missing = [x for x in missing if x not in OPTIONAL_STABLE_SOURCES]
    optional_pending = [x for x in missing if x in OPTIONAL_STABLE_SOURCES]

    issues = [
        x for x in (health.get("issues") or [])
        if x.get("code") not in FALSE_MISSING_CODES and x.get("code") != SCHEMA_CODE
    ]
    if required_missing:
        issues.append({
            "severity": "CRITICAL",
            "code": "STAGE72_MISSING_STABLE_SOURCE",
            "message": "Stage72 missing required stable sources: " + ", ".join(required_missing),
        })

    actual_schema = str(stage72.get("schema_version") or "").strip()
    expected_schema = str(schema.get("schema_version") or "").strip()
    if expected_schema and actual_schema and actual_schema != expected_schema:
        issues.append({
            "severity": "WARN",
            "code": SCHEMA_CODE,
            "message": f"Stage72 schema manifest expects v{expected_schema}, got v{actual_schema}",
        })

    critical = sum(1 for x in issues if x.get("severity") == "CRITICAL")
    warnings = sum(1 for x in issues if x.get("severity") == "WARN")
    status = "CRITICAL" if critical else ("WARN" if warnings else "HEALTHY")

    health["issues"] = issues
    health["status"] = status
    summary = health.setdefault("summary", {})
    summary["critical_issues"] = critical
    summary["warnings"] = warnings
    summary["stage72_schema_version"] = stage72.get("schema_version")
    summary["optional_stable_sources_pending"] = optional_pending
    health.setdefault("policy", {})["optional_stable_sources"] = sorted(OPTIONAL_STABLE_SOURCES)

    health_path.write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8")
    (ops / "system_health.md").write_text(render_markdown(health), encoding="utf-8")

    meta_path = ops / "stage67_last_run.json"
    meta = read_json(meta_path, {}) or {}
    meta.update({
        "system_health": status,
        "critical_issues": critical,
        "warnings": warnings,
        "stage72_schema_version": stage72.get("schema_version"),
        "optional_stable_sources_pending": optional_pending,
    })
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return health


def main() -> None:
    ops = Path(os.getenv("OPS_DIR", "ops"))
    result = reconcile(ops)
    print(json.dumps({
        "system_health": result.get("status"),
        "critical": (result.get("summary") or {}).get("critical_issues"),
        "warnings": (result.get("summary") or {}).get("warnings"),
        "optional_pending": (result.get("summary") or {}).get("optional_stable_sources_pending"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
