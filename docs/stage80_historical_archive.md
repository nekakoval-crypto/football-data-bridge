# Stage80 — PBK Historical Data Archive foundation

Status: **ACTIVE FOUNDATION — roster history + observed membership projection implemented**

## Why this exists

PBK must not depend on asking API-Football again for information it has already observed. Runtime UI/read models may keep only the latest state for speed, but historical observations must be preserved separately with provenance.

Stage79 `team_rosters.csv` remains the **current roster read model** used by Match Card and the manual lineup picker. Stage80 adds `team_roster_history.csv` as an **append-only historical archive** of every distinct roster snapshot captured by Stage79.

## Stage80 roster-history contract

- provider-free: Stage80 makes **0 API calls**;
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

## What this does not yet claim

This is still an archive foundation, not the complete football warehouse. The following remain separate future slices:

1. raw provider-response preservation with content hash/provenance and off-site retention;
2. verified transfer-source integration that can turn observation boundaries into factual transfer events where evidence exists;
3. append-only fixture / lineup / event / injury / transfer archive;
4. broader historical backfill by league/season under API-budget controls;
5. stable archive read APIs and completeness/coverage dashboards;
6. xG/xA/event-level data only where a verified source actually provides it — PBK never fabricates missing metrics.

## Relationship to existing stages

- Stage77 already preserves per-fixture player-stat and Player Grade snapshots.
- Stage78 provides provider-free Player Grade / XI Quality / Player Importance research.
- Stage79 captures current team squads for the manual lineup picker.
- Stage80 preserves historical roster observations and derives conservative observed membership intervals without additional provider traffic.

This numbering reflects the repository's actual merged state: Stage77–79 already exist and are not renumbered retroactively.
