# Stage80 — Durable Historical Transfer Archive

Status: **HISTORICAL ENRICHMENT — APPEND-ONLY, PROVIDER-FREE**

PBK persists conservatively mapped Transfermarkt transfer rows into its own durable
warehouse instead of leaving verified historical transfer evidence only inside a
temporary workflow artifact.

## Input authority

The archive consumes only the output of the existing PBK ↔ Transfermarkt entity
mapping pipeline.

A transfer row is eligible only when the player mapping is:

- `match_status = AUTO_MATCH`;
- `match_method` is one of `EXACT_NAME_CURRENT_CLUB`, `EXACT_PROFILE_NAME_DOB_CURRENT_CLUB`, or `EXACT_STATS_NAME_CURRENT_CLUB`;
- `match_confidence = HIGH`.

REVIEW, ambiguous, initial+surname and other non-authoritative candidates are never
promoted into durable transfer evidence.

Transfermarkt player/club identifiers remain their own namespace. They are never
silently converted into API-Football player/team identifiers.

## Durable dataset

Canonical PBK output:

`ops/historical_transfer_events.csv`

Each row preserves:

- deterministic `transfer_event_id`;
- PBK player ID/name;
- Transfermarkt player ID/name;
- effective transfer date and season;
- source and destination Transfermarkt club IDs/names;
- fee and market value when supplied by the source;
- mapping method/confidence;
- source snapshot/provenance hash;
- first PBK ingestion timestamp;
- explicit research/governance flags.

Missing fee, market value or club identifiers remain empty/UNKNOWN. They are never
zero-filled.

## Identity and first-observation-wins

`transfer_event_id` is a deterministic SHA-256 identity derived from PBK player,
Transfermarkt player, transfer date/season and source/destination club evidence.

Rerunning the same source snapshot is idempotent.

If a later source snapshot produces a conflicting row with the same event identity,
PBK preserves the first observed row and reports the conflict in
`ops/stage80_transfer_history_last_run.json`. It does not silently rewrite old
historical evidence.

## Current-data limitation

The upstream `dcaribou/transfermarkt-datasets` snapshot used by PBK is historical
enrichment and is not treated as current squad authority.

Therefore this archive:

- does not mutate `team_rosters.csv`;
- does not infer current membership;
- does not turn observed roster boundaries into transfer dates;
- does not replace API-Football operational authority;
- does not create probability, EV/value, signal, R1/R2/R3 eligibility, stake,
  settlement or Forward Journal state.

## Warehouse and API

Stage72 already imports every `ops/*.csv` file as a provider-free raw SQLite
projection, so the durable dataset appears as:

`raw_historical_transfer_events`

The player archive endpoint:

`GET /v1/archive/player?player_id=<PBK_PLAYER_ID>`

returns `historical_transfers` when verified rows exist. A known player without
verified transfer history receives an explicit empty list and
`verified_transfer_history = false`.

## Readiness semantics

Stage80 readiness removes
`VERIFIED_TRANSFER_EVENTS_NOT_YET_INGESTED` only when at least one valid durable HIGH-confidence transfer row from one of the approved exact-name+club methods is present.

A missing or entirely invalid dataset keeps that gap explicit. Invalid rows are
reported separately and never count as verified coverage.
