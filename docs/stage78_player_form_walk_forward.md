# Stage78 Player Form Walk-Forward

Status: **RESEARCH FOUNDATION / VALIDATION PENDING**

Purpose:

Build a deterministic, provider-free retrospective walk-forward dataset for
Player Form Grade windows using PBK-owned historical player grades and PBK16
fixture history.

Pipeline:

`player_grade_snapshots.csv`
-> PBK16 fixture identity + season provenance
-> prior terminal fixture chronology
-> Form-3 / Form-5 / Form-10 / season baseline
-> future target team result
-> walk-forward research dataset

## Time semantics

Historical player rows were often imported by PBK long after the match took
place. Therefore `observed_at_utc` is ingestion provenance and must not be
treated as the historical event-availability time for retrospective backtests.

The retrospective walk-forward reconstruction uses:

`PRIOR_TERMINAL_FIXTURE_CHRONOLOGY`

A prior row is eligible only when its fixture kickoff is strictly earlier than
the target fixture kickoff and the historical fixture is terminal
(`FT`, `AET`, `PEN`, or `FINISHED`).

The dataset explicitly records:

- `retrospective_reconstructed = true`
- `evidence_time_basis = PRIOR_TERMINAL_FIXTURE_CHRONOLOGY`
- `ingestion_observed_at_used_as_cutoff = false`

This is a historical research reconstruction, not a claim that PBK had ingested
the row before the target match in real time.

## Current production evidence

At the first real V1 build:

- grade rows: 15,828
- joined PBK16 grade rows: 11,809
- output rows: 11,809
- full Form-3 windows: 7,028
- full Form-5 windows: 6,043
- full Form-10 windows: 3,927
- leakage violations: 0
- provider calls: 0

Current provenance is scope-limited and concentrated in 2025, with coverage in
Norway, Poland, Denmark, Belgium, Austria, and Scotland. Norway currently
dominates the sample.

Therefore this dataset is sufficient to begin validation research, but it does
not establish a globally validated PBK16 Player Form Grade.

## Governance

This layer:

- is research only;
- is provider-free;
- is no-lookahead by prior terminal fixture chronology;
- creates no signal;
- mutates no canonical probability;
- changes no eligibility;
- changes no stake;
- does not mutate the Forward Journal.

The next gate is out-of-sample validation of Form-3/Form-5/Form-10 versus future
team outcomes and market residuals, with league/season scope reported
explicitly.
