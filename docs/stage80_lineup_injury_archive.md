# Stage80 — normalized lineup and injury archive

Status: **PROVIDER-FREE ARCHIVE SLICE**

This slice normalizes already-persisted PBK context evidence into dedicated append-only ledgers:

- `ops/lineup_snapshots.csv`
- `ops/injury_snapshots.csv`

No provider call is added. The stage reads only evidence PBK has already persisted in:

- `match_context_snapshots.csv`
- `rotation_snapshots.csv`

## Lineup archive contract

A lineup row represents one observed official team lineup for one fixture snapshot.

Identity:

`fixture_id + captured_at_utc + team_id + source_dataset`

The archive stores:
- fixture and kickoff;
- team and side;
- formation and coach where observed;
- normalized starting XI JSON;
- XI count;
- source dataset and snapshot type.

Expected/reconstructed XI is **not** archived as official evidence. Only already-observed official lineup evidence is eligible.

## Injury archive contract

An injury row represents one observed availability/injury statement at one captured fixture snapshot.

Identity:

`fixture_id + captured_at_utc + team_id + (player_id|player_name) + availability_type + reason + source_dataset`

The stage deduplicates duplicate items inside the same source snapshot but does not infer recovery, return date, severity or transfer status from absence in a later snapshot.

## Governance

- append-only first-observation-wins semantics;
- provider-free;
- missing identity is rejected rather than zero-filled;
- no canonical probability, EV, R1/R2/R3 eligibility, stake or Forward mutation;
- current coverage is limited by the upstream Stage55/rotation capture scope and therefore must not be presented as full 16-league coverage.

Stage80 readiness and manifest explicitly report these ledgers separately from the broader context source.
