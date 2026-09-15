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
- Stage72 automatically imports the CSV through its existing every-`ops/*.csv` policy as `raw_fixture_history_snapshots`;
- this archive does not create signals or mutate probability, EV, R1/R2/R3 eligibility, stake, settlement or Forward journal.

## What this archive proves

A row proves only what PBK's current-round collector observed at the row's `observed_at_utc` timestamp. It does not create data for times before PBK observed the fixture and it does not claim complete historical backfill.

The initial production run will seed the archive from the current rolling inventory. Subsequent successful Stage71 current-round runs append new observations instead of replacing prior ones.

Broader multi-season fixture backfill remains a separate Stage80 task under explicit source and API-budget controls.
