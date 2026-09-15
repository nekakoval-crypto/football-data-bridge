# Stage80 — PBK Historical Data Archive foundation

Status: **ACTIVE FOUNDATION — roster history + observed membership + raw-provider archive contract implemented**

## Why this exists

PBK must not depend on asking API-Football again for information it has already observed. Runtime UI/read models may keep only the latest state for speed, but historical observations must be preserved separately with provenance.

Stage79 `team_rosters.csv` remains the **current roster read model** used by Match Card and the manual lineup picker. Stage80 adds `team_roster_history.csv` as an **append-only historical archive** of every distinct roster snapshot captured by Stage79.

## Stage80 roster-history contract

- provider-free: Stage80 roster-history projection makes **0 API calls**;
- source is the already captured Stage79 roster state;
- immutable identity is `team_id + captured_at_utc + player_id`;
- a later roster capture for the same team is appended, never substituted for an earlier capture;
- rerunning the same snapshot is idempotent;
- duplicate-key drift never rewrites the first historical observation;
- missing team/player/capture identity is rejected from the archive;
- Stage72 automatically projects the CSV as `raw_team_roster_history` under the existing every-`ops/*.csv` raw import policy;
- no canonical probability, EV, R1/R2/R3 eligibility, stake, settlement or Forward mutation.

## Observed roster-membership intervals

`team_membership_intervals.csv` is a deterministic provider-free projection derived from the append-only roster history.

For each team/player it records contiguous observed roster presence with:
- first and last snapshot where the player was seen;
- previous snapshot where the player was absent, when available;
- next snapshot where the player was absent, when available;
- OPEN_LATEST versus CLOSED_BY_OBSERVED_ABSENCE;
- number of roster snapshots supporting the interval;
- deterministic interval identity and explicit evidence semantics.

These are **observation boundaries, not confirmed transfer dates**. PBK must not say a player transferred on a snapshot boundary unless a separate verified transfer source proves that fact. A leave-and-return pattern may therefore create multiple observed intervals without claiming why the player disappeared.

Stage72 automatically projects this CSV as `raw_team_membership_intervals` through the same raw CSV policy.

## Raw provider-response archive contract

The shared API-Football broker can now copy every **successful real provider response** into a content-addressed raw archive without making an additional provider request.

- enabled only when `API_FOOTBALL_ARCHIVE_DIR` points to a persistent storage location;
- canonical JSON payload gets SHA-256 identity and deterministic gzip blob storage;
- identical payload bytes share one blob, while separate real observations may keep separate provenance records;
- append-only `manifest.jsonl` stores provider, endpoint path, normalized semantic params, fetch timestamp, payload hash/size and relative blob path;
- API key and HTTP headers are never persisted;
- cache hits do not fabricate new provider observations;
- archive write failures increment broker telemetry but do not discard an otherwise valid operational football response;
- no archive path is enabled by default in CI, so a temporary runner filesystem is never mislabeled as durable storage.

**Storage gate:** the archive code/contract can be complete while durable production retention remains pending. PBK must not claim raw historical durability until `API_FOOTBALL_ARCHIVE_DIR` is backed by a persistent/off-site-retained location and a restore/readback check succeeds.

## What this does not yet claim

This is still an archive foundation, not the complete football warehouse. The following remain separate future slices:

1. provision durable/off-site-backed storage for the raw provider archive and verify restore/readback;
2. verified transfer-source integration that can turn observation boundaries into factual transfer events where evidence exists;
3. append-only fixture / lineup / event / injury / transfer archive and normalized warehouse projections;
4. broader historical backfill by league/season under API-budget controls;
5. stable archive read APIs and completeness/coverage dashboards;
6. xG/xA/event-level data only where a verified source actually provides it — PBK never fabricates missing metrics.

## Relationship to existing stages

- Stage77 already preserves per-fixture player-stat and Player Grade snapshots.
- Stage78 provides provider-free Player Grade / XI Quality / Player Importance research.
- Stage79 captures current team squads for the manual lineup picker.
- Stage80 preserves historical roster observations, derives conservative observed membership intervals, and adds the storage-neutral raw-response archive hook to the shared provider broker.

This numbering reflects the repository's actual merged state: Stage77–79 already exist and are not renumbered retroactively.
