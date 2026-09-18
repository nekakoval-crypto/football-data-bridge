#!/usr/bin/env python3
"""Stage80 — provider-free archive manifest and provenance registry.

The manifest is a governance contract for PBK historical/evidence datasets. It
never calls a provider and never mutates betting/model state. It records what a
dataset means, how rows are identified, which timestamps carry observation vs
effective-time semantics, whether the dataset is append-only/current/derived,
and whether a materialized CSV still satisfies its declared header contract.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
OUT_JSON = OPS / "stage80_archive_manifest.json"
OUT_CSV = OPS / "stage80_archive_manifest.csv"
VERSION = "PBK_STAGE80_ARCHIVE_MANIFEST_V16_PREMATCH_CONTEXT"

DATASETS = [
    {
        "dataset_id": "current_round_fixtures",
        "path": "current_round_fixtures.csv",
        "role": "CURRENT_READ_MODEL",
        "lifecycle": "ROLLING_REPLACE",
        "identity_key": ["fixture_id"],
        "observed_time_fields": ["observed_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage71 current-round capture / API-Football broker",
        "limitations": "Rolling inventory; not a historical archive by itself.",
    },
    {
        "dataset_id": "fixture_history_snapshots",
        "path": "fixture_history_snapshots.csv",
        "role": "HISTORICAL_EVIDENCE",
        "lifecycle": "APPEND_ONLY_FIRST_OBSERVATION_WINS",
        "identity_key": ["fixture_id", "observed_at_utc"],
        "observed_time_fields": ["observed_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage80 archive of already-persisted Stage71 observations",
        "limitations": "Begins when PBK observed the fixture; no pre-PBK hindsight backfill.",
    },
    {
        "dataset_id": "historical_fixtures",
        "path": "historical_fixtures.csv",
        "role": "DERIVED_WAREHOUSE",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["fixture_id"],
        "observed_time_fields": ["first_seen_at_utc", "last_seen_at_utc"],
        "effective_time_fields": ["latest_kickoff_utc"],
        "source": "Stage80 normalized projection from fixture_history_snapshots",
        "limitations": "Rebuildable convenience layer; fixture_history_snapshots remains historical evidence source-of-truth.",
    },
    {
        "dataset_id": "stage77_player_stats_backlog",
        "path": "stage77_player_stats_backlog.csv",
        "role": "DURABLE_WORK_QUEUE",
        "lifecycle": "DURABLE_STATE_MACHINE",
        "identity_key": ["fixture_id"],
        "observed_time_fields": ["first_queued_at_utc", "last_seen_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage71 terminal observation + Stage77 reconciliation",
        "limitations": "Queue evidence is not player-stat evidence; CAPTURED requires both stats and grade ledgers.",
    },
    {
        "dataset_id": "stage81_team_stats_backlog",
        "path": "stage81_team_stats_backlog.csv",
        "role": "DURABLE_WORK_QUEUE",
        "lifecycle": "DURABLE_STATE_MACHINE",
        "identity_key": ["fixture_id"],
        "observed_time_fields": ["first_queued_at_utc", "last_seen_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage71 terminal observation + Stage81 reconciliation",
        "limitations": "Queue evidence is not team-stat evidence; CAPTURED requires both HOME and AWAY team-stat ledger rows.",
    },
    {
        "dataset_id": "team_match_statistics",
        "path": "team_match_statistics.csv",
        "role": "HISTORICAL_EVIDENCE",
        "lifecycle": "APPEND_ONLY_FIRST_OBSERVATION_WINS",
        "identity_key": ["fixture_id", "team_id"],
        "observed_time_fields": ["observed_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage81 /fixtures/statistics via shared API-Football broker",
        "limitations": "Only observed finished fixtures captured under protected provider budget; missing provider metrics remain UNKNOWN and are never zero-filled.",
    },
    {
        "dataset_id": "player_stats_snapshots",
        "path": "player_stats_snapshots.csv",
        "role": "HISTORICAL_EVIDENCE",
        "lifecycle": "PERSISTED_FIXTURE_PLAYER_ROWS",
        "identity_key": ["fixture_id", "team_id", "player_id"],
        "observed_time_fields": ["observed_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage77 /fixtures/players via shared broker",
        "limitations": "Only fixtures successfully captured under protected provider budget.",
    },
    {
        "dataset_id": "player_profile_evidence",
        "path": "player_profile_evidence.csv",
        "role": "IDENTITY_ENRICHMENT_EVIDENCE",
        "lifecycle": "BOUNDED_CURRENT_TEAM_PROFILE_PROJECTION",
        "identity_key": ["team_id", "season", "player_id"],
        "observed_time_fields": ["captured_at_utc"],
        "effective_time_fields": ["season"],
        "source": "Stage80 /players?team&season plus residual /players?id&season via shared API-Football broker; residual team context comes from current PBK roster",
        "limitations": "Identity enrichment only. Residual calls are limited to current-roster player IDs still missing after team capture. Missing profile fields remain UNKNOWN. No betting/model authority.",
    },
    {
        "dataset_id": "player_profile_residual_state",
        "path": "player_profile_residual_state.csv",
        "role": "OPERATIONAL_RETRY_LEDGER",
        "lifecycle": "BOUNDED_PLAYER_PROFILE_RETRY_STATE",
        "identity_key": ["season", "player_id"],
        "observed_time_fields": ["last_attempt_at_utc"],
        "effective_time_fields": ["season"],
        "source": "Stage80 residual /players?id&season capture state",
        "limitations": "Operational retry ledger only. EMPTY responses are retried after a bounded TTL; transient ERROR rows remain retryable. Never betting/model authority.",
    },
    {
        "dataset_id": "player_grade_snapshots",
        "path": "player_grade_snapshots.csv",
        "role": "DERIVED_RESEARCH",
        "lifecycle": "DETERMINISTIC_DERIVED_ROWS",
        "identity_key": ["fixture_id", "team_id", "player_id"],
        "observed_time_fields": ["observed_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage77/78 derived from captured player stats",
        "limitations": "Research-derived grade; not raw provider fact and not canonical authority.",
    },
    {
        "dataset_id": "epl_referee_profiles_research",
        "path": "epl_referee_profiles_research.csv",
        "role": "RESEARCH_ENRICHMENT",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["referee"],
        "observed_time_fields": [],
        "effective_time_fields": ["first_date", "last_date"],
        "source": "Stage80 Football-Data EPL referee research projection",
        "limitations": "EPL_ONLY 2017/18-2025/26 descriptive aggregates. No causal/bias authority; penalties unavailable; other Top-5 leagues remain UNKNOWN.",
    },
    {
        "dataset_id": "epl_referee_team_splits_research",
        "path": "epl_referee_team_splits_research.csv",
        "role": "RESEARCH_ENRICHMENT",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["referee", "team"],
        "observed_time_fields": [],
        "effective_time_fields": ["first_date", "last_date"],
        "source": "Stage80 Football-Data EPL referee×team research projection",
        "limitations": "EPL_ONLY historical association rows. Small samples remain visible; no observed split is treated as referee bias or betting authority.",
    },
    {
        "dataset_id": "top5_referee_fixture_history",
        "path": "top5_referee_fixture_history.csv",
        "role": "HISTORICAL_ENRICHMENT",
        "lifecycle": "RESUMABLE_PROVIDER_BACKFILL",
        "identity_key": ["fixture_id"],
        "observed_time_fields": ["captured_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage80 API-Football /fixtures?league&season Top-5 9-season referee backfill",
        "limitations": "Historical research/backfill only. Referee is provider text without a stable referee ID; missing referee values remain UNKNOWN. No cards, fouls or penalty counts are inferred from this endpoint.",
    },
    {
        "dataset_id": "top5_referee_profiles_research",
        "path": "top5_referee_profiles_research.csv",
        "role": "RESEARCH_ENRICHMENT",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["provider_league_id", "referee"],
        "observed_time_fields": [],
        "effective_time_fields": ["first_date", "last_date"],
        "source": "Stage80 projection from API-Football Top-5 referee fixture history",
        "limitations": "League-scoped exact referee text only. Descriptive result/goal aggregates; cards, fouls and penalties unavailable; no bias or betting authority.",
    },
    {
        "dataset_id": "top5_referee_team_splits_research",
        "path": "top5_referee_team_splits_research.csv",
        "role": "RESEARCH_ENRICHMENT",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["provider_league_id", "referee", "team_id"],
        "observed_time_fields": [],
        "effective_time_fields": ["first_date", "last_date"],
        "source": "Stage80 projection from API-Football Top-5 referee fixture history",
        "limitations": "League/referee/team historical association only. Small samples remain visible and are never treated as causation or referee bias.",
    },
    {
        "dataset_id": "stage80_top5_referee_backfill_state",
        "path": "stage80_top5_referee_backfill_state.csv",
        "role": "OPERATIONAL_RETRY_LEDGER",
        "lifecycle": "DURABLE_LEAGUE_SEASON_STATE",
        "identity_key": ["provider_league_id", "season"],
        "observed_time_fields": ["last_attempt_at_utc"],
        "effective_time_fields": ["season"],
        "source": "Stage80 Top-5 referee historical backfill state",
        "limitations": "Operational resume state only; not match evidence and never betting/model authority.",
    },
    {
        "dataset_id": "top5_prematch_context_research",
        "path": "top5_prematch_context_research.csv",
        "role": "RESEARCH_ENRICHMENT",
        "lifecycle": "DETERMINISTIC_NO_LOOKAHEAD_PROJECTION",
        "identity_key": ["historical_match_id"],
        "observed_time_fields": [],
        "effective_time_fields": ["date_iso", "time_local"],
        "source": "Stage80 Football-Data Top-5 9-season no-lookahead pre-match context projection",
        "limitations": "Historical research only. Every row uses strictly earlier calendar dates within league-season; same-day results are excluded. No probability, EV/value, eligibility, stake or Forward authority.",
    },
    {
        "dataset_id": "statsbomb_player_xg_xa",
        "path": "statsbomb_player_xg_xa.csv",
        "role": "RESEARCH_ENRICHMENT",
        "lifecycle": "DERIVED_EXTERNAL_OPEN_DATA_PROJECTION",
        "identity_key": ["record_id"],
        "observed_time_fields": [],
        "effective_time_fields": ["match_date"],
        "source": "Stage91 derived from local StatsBomb Open Data event files",
        "limitations": "StatsBomb identity namespace only. xG is shot.statsbomb_xg; xA is derived by joining pass event id to shot.key_pass_id and assigning the shot xG. Research-only; attribution required; no PBK/API-Football identity mapping or betting authority.",
    },
    {
        "dataset_id": "statsbomb_pbk_player_mapping_candidates",
        "path": "statsbomb_pbk_player_mapping_candidates.csv",
        "role": "RESEARCH_IDENTITY_MAPPING",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["statsbomb_player_id"],
        "observed_time_fields": [],
        "effective_time_fields": [],
        "source": "Stage92 conservative StatsBomb → verified Transfermarkt → PBK player bridge",
        "limitations": "Only AUTO_MATCH/HIGH exact full-name matches through the verified Transfermarkt bridge are authoritative for mapped research. Initial+surname matches remain REVIEW only.",
    },
    {
        "dataset_id": "pbk_player_xg_xa_research",
        "path": "pbk_player_xg_xa_research.csv",
        "role": "RESEARCH_ENRICHMENT",
        "lifecycle": "DETERMINISTIC_MAPPED_PROJECTION",
        "identity_key": ["pbk_player_id", "statsbomb_record_id"],
        "observed_time_fields": [],
        "effective_time_fields": ["match_date"],
        "source": "Stage92 AUTO_MATCH/HIGH projection from Stage91 StatsBomb player xG/xA",
        "limitations": "Research-only advanced metrics. xG is StatsBomb source metric; xA is derived xG Assisted. No betting/model authority is granted.",
    },
    {
        "dataset_id": "historical_players",
        "path": "historical_players.csv",
        "role": "DERIVED_WAREHOUSE",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["player_id"],
        "observed_time_fields": ["first_seen_at_utc", "last_seen_at_utc"],
        "effective_time_fields": [],
        "source": "Stage80 normalized projection from team_roster_history + player_stats_snapshots",
        "limitations": "Observed player directory only; does not infer current team, exact transfer dates, xG or xA.",
    },
    {
        "dataset_id": "pbk_transfermarkt_player_identity",
        "path": "pbk_transfermarkt_player_identity.csv",
        "role": "VERIFIED_IDENTITY_BRIDGE",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["pbk_player_id", "transfermarkt_player_id"],
        "observed_time_fields": [],
        "effective_time_fields": [],
        "source": "Stage80 conservative PBK ↔ Transfermarkt AUTO_MATCH/HIGH identity projection",
        "limitations": "Identity bridge only. Approved methods include exact catalog name+club, exact API-Football profile full-name+DOB+club, or exact non-abbreviated match-stat name+club; no fuzzy authority and no betting/model authority.",
    },
    {
        "dataset_id": "historical_transfer_events",
        "path": "historical_transfer_events.csv",
        "role": "HISTORICAL_ENRICHMENT",
        "lifecycle": "APPEND_ONLY_FIRST_OBSERVATION_WINS",
        "identity_key": ["transfer_event_id"],
        "observed_time_fields": ["ingested_at_utc"],
        "effective_time_fields": ["transfer_date"],
        "source": "Stage80 durable projection from conservative PBK ↔ Transfermarkt AUTO_MATCH/HIGH mapping",
        "limitations": "Historical enrichment only; Transfermarkt IDs remain separate from API-Football IDs and source snapshot age prevents current-squad authority.",
    },
    {
        "dataset_id": "team_rosters",
        "path": "team_rosters.csv",
        "role": "CURRENT_READ_MODEL",
        "lifecycle": "LATEST_TEAM_SNAPSHOT",
        "identity_key": ["team_id", "player_id"],
        "observed_time_fields": ["captured_at_utc"],
        "effective_time_fields": [],
        "source": "Stage79 /players/squads via shared broker",
        "limitations": "Latest roster only; use team_roster_history for historical membership evidence.",
    },
    {
        "dataset_id": "team_roster_history",
        "path": "team_roster_history.csv",
        "role": "HISTORICAL_EVIDENCE",
        "lifecycle": "APPEND_ONLY_FIRST_OBSERVATION_WINS",
        "identity_key": ["team_id", "captured_at_utc", "player_id"],
        "observed_time_fields": ["captured_at_utc"],
        "effective_time_fields": [],
        "source": "Stage80 archive of already-captured Stage79 roster snapshots",
        "limitations": "Observed squad membership, not an exact transfer-date claim.",
    },
    {
        "dataset_id": "team_membership_intervals",
        "path": "team_membership_intervals.csv",
        "role": "DERIVED_RESEARCH",
        "lifecycle": "DETERMINISTIC_PROJECTION",
        "identity_key": ["interval_id"],
        "observed_time_fields": ["first_seen_at_utc", "last_seen_at_utc"],
        "effective_time_fields": [],
        "source": "Stage80 derived from team_roster_history",
        "limitations": "Observed presence intervals are not verified transfer events.",
    },
    {
        "dataset_id": "lineup_snapshots",
        "path": "lineup_snapshots.csv",
        "role": "HISTORICAL_EVIDENCE",
        "lifecycle": "APPEND_ONLY_FIRST_OBSERVATION_WINS",
        "identity_key": ["fixture_id", "captured_at_utc", "team_id", "source_dataset"],
        "observed_time_fields": ["captured_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage80 normalized from already-persisted Stage55 context + rotation snapshots",
        "limitations": "Only official lineup observations already captured by PBK; expected XI is not archived as official evidence.",
    },
    {
        "dataset_id": "injury_snapshots",
        "path": "injury_snapshots.csv",
        "role": "HISTORICAL_EVIDENCE",
        "lifecycle": "APPEND_ONLY_FIRST_OBSERVATION_WINS",
        "identity_key": ["fixture_id", "captured_at_utc", "team_id", "player_id", "availability_type", "reason", "source_dataset"],
        "observed_time_fields": ["captured_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage80 normalized from already-persisted Stage55 injury evidence",
        "limitations": "Provider availability labels/reasons are archived as observed facts; absence from a later snapshot is not inferred as recovery.",
    },
    {
        "dataset_id": "stage80_match_event_backlog",
        "path": "stage80_match_event_backlog.csv",
        "role": "DURABLE_WORK_QUEUE",
        "lifecycle": "DURABLE_STATE_MACHINE",
        "identity_key": ["fixture_id"],
        "observed_time_fields": ["first_queued_at_utc", "last_seen_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage71 terminal observation + Stage80 event capture reconciliation",
        "limitations": "Queue evidence is not event evidence; CAPTURED requires at least one normalized provider event row.",
    },
    {
        "dataset_id": "match_event_snapshots",
        "path": "match_event_snapshots.csv",
        "role": "HISTORICAL_EVIDENCE",
        "lifecycle": "APPEND_ONLY_FIRST_OBSERVATION_WINS",
        "identity_key": ["event_id"],
        "observed_time_fields": ["observed_at_utc"],
        "effective_time_fields": ["kickoff_utc"],
        "source": "Stage80 /fixtures/events via shared API-Football broker",
        "limitations": "Only terminal fixtures captured under protected provider budget; empty provider responses remain retryable and are not converted to fake no-event evidence.",
    },
    {
        "dataset_id": "match_context_snapshots",
        "path": "match_context_snapshots.csv",
        "role": "HISTORICAL_EVIDENCE",
        "lifecycle": "APPEND_ONLY_BY_FORWARD_AND_SNAPSHOT_TYPE",
        "identity_key": ["forward_id", "snapshot_type"],
        "observed_time_fields": ["captured_at_utc"],
        "effective_time_fields": ["current_kickoff_utc"],
        "source": "Stage55 timestamped context via shared broker",
        "limitations": "Canonical-forward scope only; not complete 16-league context coverage.",
    },
    {
        "dataset_id": "context_latest",
        "path": "context_latest.csv",
        "role": "CURRENT_READ_MODEL",
        "lifecycle": "LATEST_PROJECTION",
        "identity_key": ["forward_id"],
        "observed_time_fields": ["captured_at_utc"],
        "effective_time_fields": ["current_kickoff_utc"],
        "source": "Stage55/56 latest projection from context snapshots",
        "limitations": "Convenience read model; historical evidence remains match_context_snapshots.",
    },
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def inspect_csv(path: Path, contract: dict) -> dict:
    if not path.exists():
        return {
            "present": False,
            "row_count": None,
            "columns": [],
            "missing_required_fields": [],
            "contract_status": "PENDING_MATERIALIZATION",
        }
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = list(reader.fieldnames or [])
        row_count = sum(1 for _ in reader)
    required = list(dict.fromkeys(
        contract["identity_key"] + contract["observed_time_fields"] + contract["effective_time_fields"]
    ))
    missing = [field for field in required if field not in columns]
    return {
        "present": True,
        "row_count": row_count,
        "columns": columns,
        "missing_required_fields": missing,
        "contract_status": "ATTENTION" if missing else "OK",
    }


def build_manifest(ops: Path = OPS, raw_archive_dir: str | None = None) -> dict:
    entries = []
    attention = 0
    pending = 0
    for declared in DATASETS:
        runtime = inspect_csv(Path(ops) / declared["path"], declared)
        entry = {**declared, **runtime}
        entry["identity_key_text"] = "+".join(declared["identity_key"])
        entry["observed_time_fields_text"] = ",".join(declared["observed_time_fields"])
        entry["effective_time_fields_text"] = ",".join(declared["effective_time_fields"])
        entries.append(entry)
        attention += runtime["contract_status"] == "ATTENTION"
        pending += runtime["contract_status"] == "PENDING_MATERIALIZATION"

    local_configured = bool((raw_archive_dir if raw_archive_dir is not None else os.getenv("API_FOOTBALL_ARCHIVE_DIR", "")).strip())
    verify_path = Path(ops) / "stage80_raw_archive_storage_last_run.json"
    s3_verified = False
    verify = {}
    if verify_path.exists():
        try:
            verify = json.loads(verify_path.read_text(encoding="utf-8"))
            s3_verified = (
                verify.get("backend") == "S3"
                and verify.get("status") == "READY"
                and bool(verify.get("readback_match"))
                and bool(verify.get("durable"))
            )
        except (OSError, json.JSONDecodeError, TypeError):
            verify = {}
    configured = local_configured or s3_verified
    entries.append({
        "dataset_id": "raw_api_football_payloads",
        "path": "EXTERNAL_DURABLE_STORAGE",
        "role": "RAW_PROVIDER_ARCHIVE",
        "lifecycle": "CONTENT_ADDRESSED_APPEND_ONLY",
        "identity_key": ["payload_sha256"],
        "identity_key_text": "payload_sha256",
        "observed_time_fields": ["observed_at_utc"],
        "observed_time_fields_text": "observed_at_utc",
        "effective_time_fields": [],
        "effective_time_fields_text": "",
        "source": "API-Football broker successful real responses",
        "limitations": "Physical durable storage is separate from Git; cache hits do not create false provider observations. S3/R2 readiness requires write/readback/hash verification telemetry.",
        "present": configured,
        "row_count": None,
        "columns": [],
        "missing_required_fields": [],
        "storage_backend": "LOCAL" if local_configured else ("S3" if s3_verified else None),
        "storage_verified_at_utc": verify.get("run_at_utc") if s3_verified else None,
        "contract_status": "CONFIGURED" if configured else "PENDING_DURABLE_STORAGE",
    })
    if not configured:
        pending += 1

    return {
        "version": VERSION,
        "generated_at_utc": iso_now(),
        "status": "ATTENTION" if attention else "OK",
        "datasets": entries,
        "summary": {
            "declared_datasets": len(entries),
            "materialized_csv_datasets": sum(1 for e in entries if e["path"].endswith(".csv") and e["present"]),
            "pending_materializations_or_storage": pending,
            "contract_attention": attention,
        },
        "provider_calls": 0,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }


def write_outputs(report: dict, ops: Path = OPS) -> None:
    ops.mkdir(parents=True, exist_ok=True)
    (ops / OUT_JSON.name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = [
        "dataset_id", "path", "role", "lifecycle", "identity_key_text",
        "observed_time_fields_text", "effective_time_fields_text", "source",
        "present", "row_count", "contract_status", "missing_required_fields", "limitations",
    ]
    temp = ops / (OUT_CSV.name + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for entry in report["datasets"]:
            row = dict(entry)
            row["missing_required_fields"] = ",".join(entry.get("missing_required_fields") or [])
            writer.writerow(row)
    temp.replace(ops / OUT_CSV.name)


def main():
    report = build_manifest()
    write_outputs(report)
    print(json.dumps({"status": report["status"], **report["summary"], "provider_calls": 0}, ensure_ascii=False))
    if report["status"] == "ATTENTION":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
