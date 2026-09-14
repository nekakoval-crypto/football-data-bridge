"""Refresh dynamic status and scores for tracked current-round fixtures."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError
from stage72_build_data_layer import today_status

OPS = Path(os.getenv("OPS_DIR", "ops"))
BASE = OPS / "current_round_fixtures.csv"
OVERLAY = OPS / "live_fixture_overlay.csv"
META = OPS / "live_fixture_overlay_last_run.json"
FIELDS = [
    "fixture_id", "source_status", "status", "score_home", "score_away",
    "elapsed", "observed_at_utc", "live_observed_at_utc",
    "live_freshness_status",
]
TERMINAL = {"finished", "postponed", "cancelled", "abandoned", "awarded", "walkover"}
ACTIVE = {"live", "suspended", "interrupted"}


def parse_time(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row.get("fixture_id") or ""))
    temporary.replace(path)


def candidates(base_rows, previous, now):
    result = []
    for row in base_rows:
        kickoff = parse_time(row.get("kickoff_utc"))
        if not kickoff:
            continue
        old = previous.get(str(row.get("fixture_id") or "")) or row
        status = old.get("status")
        in_window = kickoff - timedelta(minutes=15) <= now <= kickoff + timedelta(hours=4)
        active_until_limit = status in ACTIVE and now <= kickoff + timedelta(hours=4)
        if in_window or active_until_limit:
            result.append(row)
    return result


def provider_row(item, observed):
    fixture = item.get("fixture") or {}
    status = fixture.get("status") or {}
    goals = item.get("goals") or {}
    raw = status.get("short")
    return {
        "fixture_id": str(fixture.get("id") or ""),
        "source_status": raw or None,
        "status": today_status(raw),
        "score_home": goals.get("home"),
        "score_away": goals.get("away"),
        "elapsed": status.get("elapsed"),
        "observed_at_utc": observed,
        "live_observed_at_utc": observed if today_status(raw) in ACTIVE else None,
        "live_freshness_status": "fresh",
    }


def refresh(base_rows, previous_rows, get, now):
    previous = {str(row.get("fixture_id") or ""): row for row in previous_rows}
    tracked = candidates(base_rows, previous, now)
    tracked_ids = {str(row.get("fixture_id") or "") for row in tracked}
    output = dict(previous)
    updated_ids = set()
    warnings = []
    calls = 0
    dates = sorted({parse_time(row["kickoff_utc"]).date().isoformat() for row in tracked})
    for date in dates:
        calls += 1
        try:
            payload = get("/fixtures", {"date": date, "timezone": "UTC"}, force_refresh=True)
            for item in payload.get("response", []):
                current = provider_row(item, iso(now))
                if current["fixture_id"] in tracked_ids:
                    previous_state = output.get(current["fixture_id"]) or {}
                    if previous_state.get("status") in TERMINAL and current["status"] in ACTIVE:
                        continue
                    output[current["fixture_id"]] = current
                    updated_ids.add(current["fixture_id"])
        except (ApiFootballBrokerError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            warnings.append(f"{date}: {exc}")
    for fixture_id in tracked_ids - updated_ids:
        if fixture_id in output:
            output[fixture_id]["live_freshness_status"] = "stale"
    return list(output.values()), {
        "provider_calls": calls,
        "candidate_fixtures": len(tracked),
        "updated_fixtures": len(updated_ids),
        "skipped_no_candidates": not tracked,
        "budget_exhausted": any("budget exhausted" in warning.lower() for warning in warnings),
        "observed_at_utc": iso(now),
        "warnings": warnings,
    }


def main():
    now = datetime.now(timezone.utc)
    state_path = OPS / "stage71_observation_state.json"
    state = audit.read(state_path)
    budget = audit.Budget(
        s53.api_get, state, now,
        int(os.getenv("STAGE71_MAX_API_CALLS", "60")),
        int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "180")),
        checkpoint=lambda value: audit.save(state_path, value),
    )
    rows, meta = refresh(read_csv(BASE), read_csv(OVERLAY), budget, now)
    audit.save(state_path, state)
    write_csv(OVERLAY, rows)
    meta.update({"status": "ATTENTION" if meta["warnings"] else "OK",
                 "api_day_calls": state.get("api_day_calls", 0),
                 "provider_polling": True})
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
