# Stage80 Fixture History

Status: **IMPLEMENTED ARCHIVE SLICE — pending first production materialization**

`ops/current_round_fixtures.csv` is a rolling provider-defined read model. It is useful for Today/LIVE and current-round work, but it is not a historical store: older rounds and earlier fixture states can disappear when the next current-round observation replaces the file.

Stage80 therefore preserves the already-paid Stage71 observations in `ops/fixture_history_snapshots.csv`.

## Contract

- **0 additional provider calls**: source is only the persisted `current_round_fixtures.csv` produced by Stage71;
- Stage71 runs the archive helper immediately after a successful current-round capture;
- immutable observation identity is `fixture_id + observed_at_utc`;
- the same fixture may legitimately have many observations over time (for example NS, rescheduled, LIVE/FT state as exposed by the current-round collector);
- rerunning the same observation is idempotent;
- when the same archive identity appears with drifted display values, the first persisted historical observation wins rather than being rewritten;
- rows without fixture identity or observation timestamp are rejected and reported;
- source fields are preserved together with `archive_version`;
- referee and venue are preserved from the same already-paid API-Football `/fixtures` payload when the provider supplies them; missing values remain UNKNOWN/empty and cause **0 additional provider calls**;
- Stage72 automatically imports the CSV through its existing every-`ops/*.csv` policy as `raw_fixture_history_snapshots`;
- this archive does not create signals or mutate probability, EV, R1/R2/R3 eligibility, stake, settlement or Forward journal.

## Archive Readiness

Stage80 Readiness treats fixture history as its own evidence layer and reports:

- whether `fixture_history_snapshots.csv` has been materialized in production;
- total valid fixture observations;
- unique fixture IDs represented in history;
- unique observation timestamps/runs;
- number of fixtures ever observed in a terminal state;
- invalid rows missing either `fixture_id` or `observed_at_utc`.

Before the first production seed, readiness reports `FIXTURE_HISTORY_WAITING_FIRST_PRODUCTION_SEED` instead of presenting a misleading 0-row archive as complete. Invalid archive identities raise `FIXTURE_HISTORY_INVALID_IDENTITY_ROWS`.

## What this archive proves

A row proves only what PBK's current-round collector observed at the row's `observed_at_utc` timestamp. It does not create data for times before PBK observed the fixture and it does not claim complete historical backfill.

The initial production run will seed the archive from the current rolling inventory. Subsequent successful Stage71 current-round runs append new observations instead of replacing prior ones.

Broader multi-season fixture backfill remains a separate Stage80 task under explicit source and API-budget controls.
