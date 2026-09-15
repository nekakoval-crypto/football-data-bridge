# Stage80 Archive Manifest / Provenance Registry

Status: **IMPLEMENTED GOVERNANCE SLICE — provider-free**

Stage80 now maintains a machine-checkable registry of historical/evidence datasets instead of relying on human memory about which CSV is authoritative and what its timestamps mean.

## Purpose

For every declared dataset the registry records:

- semantic role: historical evidence, current read model, durable work queue, derived research or raw provider archive;
- lifecycle: append-only, rolling/latest, deterministic projection or durable state machine;
- row identity key;
- observation timestamp field(s);
- effective/event timestamp field(s);
- source/provenance;
- runtime presence and row count for materialized CSVs;
- header-contract status and missing required fields;
- explicit limitations.

Outputs:

- `ops/stage80_archive_manifest.json`
- `ops/stage80_archive_manifest.csv`

## Integrity semantics

A declared dataset that has not yet materialized is `PENDING_MATERIALIZATION`; this is not treated as corruption.

A dataset that **does** exist but no longer contains a declared identity, observation-time or effective-time field is `ATTENTION`. The manifest command exits non-zero in that case so CI/operational governance cannot silently accept provenance drift.

The raw API-Football archive is represented as `EXTERNAL_ENV:API_FOOTBALL_ARCHIVE_DIR`; the real server filesystem path is never written to Git outputs. `PENDING_DURABLE_STORAGE` remains explicit until durable storage is configured.

## Important distinctions

- `current_round_fixtures.csv` is a rolling read model; historical fixture evidence belongs in `fixture_history_snapshots.csv`.
- `team_rosters.csv` is latest-state reference data; historical roster evidence belongs in `team_roster_history.csv`.
- `stage77_player_stats_backlog.csv` is a durable work queue, not proof that player stats were captured.
- `player_grade_snapshots.csv` and `team_membership_intervals.csv` are derived research layers, not raw provider facts.
- `match_context_snapshots.csv` is already append-only by `(forward_id, snapshot_type)` and remains the historical context evidence source; `context_latest.csv` is only a convenience read model.
- observed roster absence is not relabelled as a confirmed transfer.
- no xG/xA field is declared as factual until a verified source actually supplies it.

## Safety

The manifest is provider-free (`provider_calls=0`) and cannot create signals or mutate probability, EV, R1/R2/R3 eligibility, stake, settlement or the Forward journal.
