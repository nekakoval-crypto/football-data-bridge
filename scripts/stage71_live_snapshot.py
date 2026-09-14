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
    "live_freshness_status", "red_cards_home", "red_cards_away",
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


def _event_identity(fixture_id, event):
    team = event.get("team") or {}
    player = event.get("player") or {}
    clock = event.get("time") or {}
    return (str(fixture_id), team.get("id"), player.get("id"),
            event.get("type"), event.get("detail"),
            clock.get("elapsed"), clock.get("extra"))


def _red_card_counts(item):
    events = item.get("events")
    if not isinstance(events, list):
        return None, None
    fixture = item.get("fixture") or {}
    teams = item.get("teams") or {}
    home_id = (teams.get("home") or {}).get("id")
    away_id = (teams.get("away") or {}).get("id")
    home = away = 0
    seen = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        detail = " ".join(str(event.get("detail") or "").split()).casefold()
        if detail not in {"red card", "yellow-red card"}:
            continue
        identity = _event_identity(fixture.get("id"), event)
        if identity in seen:
            continue
        seen.add(identity)
        team_id = (event.get("team") or {}).get("id")
        if team_id == home_id:
            home += 1
        elif team_id == away_id:
            away += 1
    return home, away


def provider_row(item, observed):
    fixture = item.get("fixture") or {}
    status = fixture.get("status") or {}
    goals = item.get("goals") or {}
    raw = status.get("short")
    red_home, red_away = _red_card_counts(item)
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
        "red_cards_home": red_home,
        "red_cards_away": red_away,
    }


def refresh(base_rows, previous_rows, get, now):
    previous = {str(row.get("fixture_id") or ""): row for row in previous_rows}
    tracked = candidates(base_rows, previous, now)
    tracked_ids = {str(row.get("fixture_id") or "") for row in tracked}
    output = dict(previous)
    updated_ids = set()
    warnings = []
    calls = 0
    def priority(row):
        old = previous.get(str(row.get("fixture_id") or "")) or row
        status = old.get("status")
        kickoff = parse_time(row.get("kickoff_utc"))
        active = status in ACTIVE
        post_kickoff = kickoff and kickoff <= now
        return (0 if active else 1 if post_kickoff else 2, kickoff or now)

    tracked.sort(key=priority)
    batches = [tracked[i:i + 20] for i in range(0, len(tracked), 20)]
    max_calls = getattr(get, "limit", None)
    calls_used = getattr(get, "calls", 0)
    daily_limit = getattr(get, "daily_limit", None)
    daily_calls = getattr(get, "state", {}).get("api_day_calls", 0)
    if max_calls is not None:
        max_calls = min(max_calls - calls_used,
                        daily_limit - daily_calls if daily_limit is not None else max_calls)
        batches = batches[:max(0, max_calls)]
        if max_calls <= 0 and tracked:
            warnings.append("Stage71 API budget exhausted; retry next run")
    for batch in batches:
        ids = "-".join(str(row.get("fixture_id")) for row in batch)
        calls += 1
        try:
            payload = get("/fixtures", {"ids": ids, "timezone": "UTC"}, force_refresh=True)
            for item in payload.get("response", []):
                current = provider_row(item, iso(now))
                if current["fixture_id"] in tracked_ids:
                    previous_state = output.get(current["fixture_id"]) or {}
                    if previous_state.get("status") in TERMINAL and current["status"] in ACTIVE:
                        continue
                    output[current["fixture_id"]] = current
                    updated_ids.add(current["fixture_id"])
        except (ApiFootballBrokerError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            warnings.append(f"{ids}: {exc}")
    for fixture_id in tracked_ids - updated_ids:
        if fixture_id in output:
            output[fixture_id]["live_freshness_status"] = "stale"
    skipped = tracked[len(batches) * 20:]
    if skipped:
        warnings.append(f"skipped {len(skipped)} candidate fixtures due to provider budget")
    return list(output.values()), {
        "provider_calls": calls,
        "candidate_fixtures": len(tracked),
        "updated_fixtures": len(updated_ids),
        "batch_size": 20,
        "skipped_fixtures": len(skipped),
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
