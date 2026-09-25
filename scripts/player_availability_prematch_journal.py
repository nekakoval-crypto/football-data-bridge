#!/usr/bin/env python3
"""Provider-free Prematch Availability Journal V1.

Materializes explicit player availability evidence from already persisted
Stage55 pre-match context snapshots.

Evidence rules:
- injury rows observed no later than kickoff -> ABSENT;
- players explicitly present in an official XI observed no later than kickoff
  -> PRESENT;
- absence from XI never implies ABSENT;
- no roster/nationality/travel inference;
- append-only/idempotent journal;
- research-only, no signal/probability/eligibility/stake mutation.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
SOURCE = OPS / "match_context_snapshots.csv"
OUT = OPS / "player_availability_prematch_events.csv"
META = OPS / "player_availability_prematch_journal_last_run.json"

VERSION = "PBK_PLAYER_AVAILABILITY_PREMATCH_JOURNAL_V1"
FIELDS = [
    "event_id",
    "forward_id",
    "fixture_id",
    "kickoff_utc",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "state",
    "availability_type",
    "reason",
    "observed_at_utc",
    "snapshot_type",
    "source",
    "evidence_type",
    "prematch_known",
    "no_lookahead",
    "research_only",
]


def parse_dt(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv_atomic(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def parse_json_list(value):
    try:
        data = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def event_id(parts):
    raw = "|".join(str(x or "") for x in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def normalized_event(
    *,
    snapshot,
    team_id,
    team_name,
    player_id,
    player_name,
    state,
    availability_type="",
    reason="",
    source,
    evidence_type,
):
    observed = str(snapshot.get("captured_at_utc") or "").strip()
    fixture_id = str(snapshot.get("api_fixture_id") or "").strip()
    eid = event_id(
        [
            fixture_id,
            team_id,
            player_id,
            state,
            observed,
            source,
            availability_type,
            reason,
        ]
    )
    return {
        "event_id": eid,
        "forward_id": str(snapshot.get("forward_id") or "").strip(),
        "fixture_id": fixture_id,
        "kickoff_utc": str(snapshot.get("current_kickoff_utc") or "").strip(),
        "team_id": str(team_id or "").strip(),
        "team_name": str(team_name or "").strip(),
        "player_id": str(player_id or "").strip(),
        "player_name": str(player_name or "").strip(),
        "state": state,
        "availability_type": str(availability_type or "").strip(),
        "reason": str(reason or "").strip(),
        "observed_at_utc": observed,
        "snapshot_type": str(snapshot.get("snapshot_type") or "").strip(),
        "source": source,
        "evidence_type": evidence_type,
        "prematch_known": "YES",
        "no_lookahead": "YES",
        "research_only": "YES",
    }


def events_from_snapshot(snapshot):
    observed = parse_dt(snapshot.get("captured_at_utc"))
    kickoff = parse_dt(snapshot.get("current_kickoff_utc"))
    if observed is None or kickoff is None:
        return [], "INVALID_TIME"
    if observed > kickoff:
        return [], "LOOKAHEAD_VIOLATION"

    events = []

    for item in parse_json_list(snapshot.get("injuries_json")):
        if not isinstance(item, dict):
            continue
        pid = str(item.get("player_id") or "").strip()
        tid = str(item.get("team_id") or "").strip()
        if not pid or not tid:
            continue
        events.append(
            normalized_event(
                snapshot=snapshot,
                team_id=tid,
                team_name=item.get("team"),
                player_id=pid,
                player_name=item.get("player"),
                state="ABSENT",
                availability_type=item.get("type"),
                reason=item.get("reason"),
                source="STAGE55_PREMATCH_INJURY",
                evidence_type="EXPLICIT_PROVIDER_INJURY",
            )
        )

    if str(snapshot.get("lineups_available") or "").upper() in {"YES", "TRUE", "1"}:
        for side in ("home", "away"):
            tid = str(snapshot.get(f"{side}_team_id") or "").strip()
            team_name = str(snapshot.get(f"{side}_team") or "").strip()
            if not tid:
                continue
            for player in parse_json_list(snapshot.get(f"{side}_start_xi_json")):
                if not isinstance(player, dict):
                    continue
                pid = str(player.get("id") or player.get("player_id") or "").strip()
                if not pid:
                    continue
                events.append(
                    normalized_event(
                        snapshot=snapshot,
                        team_id=tid,
                        team_name=team_name,
                        player_id=pid,
                        player_name=player.get("name") or player.get("player_name"),
                        state="PRESENT",
                        source="STAGE55_OFFICIAL_XI",
                        evidence_type="EXPLICIT_OFFICIAL_STARTER",
                    )
                )

    return events, "OK"


def merge_events(existing, incoming):
    merged = {}
    invalid_existing = 0
    for row in existing:
        eid = str(row.get("event_id") or "").strip()
        if not eid:
            invalid_existing += 1
            continue
        merged[eid] = {field: row.get(field, "") for field in FIELDS}

    added = 0
    for row in incoming:
        eid = str(row.get("event_id") or "").strip()
        if not eid or not row.get("player_id") or not row.get("team_id"):
            continue
        if eid in merged:
            continue
        merged[eid] = {field: row.get(field, "") for field in FIELDS}
        added += 1

    rows = [merged[key] for key in sorted(merged)]
    return rows, added, invalid_existing


def main():
    snapshots = read_csv(SOURCE)
    existing = read_csv(OUT)

    incoming = []
    invalid_time = 0
    lookahead_violations = 0
    eligible_snapshots = 0

    for snapshot in snapshots:
        events, status = events_from_snapshot(snapshot)
        if status == "INVALID_TIME":
            invalid_time += 1
            continue
        if status == "LOOKAHEAD_VIOLATION":
            lookahead_violations += 1
            continue
        eligible_snapshots += 1
        incoming.extend(events)

    rows, added, invalid_existing = merge_events(existing, incoming)
    write_csv_atomic(OUT, rows)

    state_counts = {}
    source_counts = {}
    for row in rows:
        state_counts[row["state"]] = state_counts.get(row["state"], 0) + 1
        source_counts[row["source"]] = source_counts.get(row["source"], 0) + 1

    report = {
        "version": VERSION,
        "run_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "OK" if lookahead_violations == 0 and invalid_existing == 0 else "ATTENTION",
        "source_snapshots": len(snapshots),
        "eligible_prematch_snapshots": eligible_snapshots,
        "invalid_time_snapshots": invalid_time,
        "lookahead_violations": lookahead_violations,
        "incoming_events": len(incoming),
        "new_events": added,
        "total_events": len(rows),
        "state_counts": state_counts,
        "source_counts": source_counts,
        "invalid_existing_events": invalid_existing,
        "append_only": True,
        "absence_from_xi_implies_absent": False,
        "roster_inference_used": False,
        "nationality_inference_used": False,
        "travel_inference_used": False,
        "provider_calls": 0,
        "no_lookahead": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    META.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "OK":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
