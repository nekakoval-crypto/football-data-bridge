# Stage80 Historical Fixture Catalog

Status: **IMPLEMENTED DERIVED WAREHOUSE SLICE — production materialization pending**

`ops/fixture_history_snapshots.csv` is append-only historical evidence. It may contain many observations of the same fixture over time. The normalized fixture catalog compacts those observations into one deterministic row per fixture for Stage72 and downstream analytics.

Output: `ops/historical_fixtures.csv`.

## Semantics

For each fixture the projection records:

- first and last PBK observation time;
- first observed kickoff and latest observed kickoff;
- whether a kickoff change/reschedule was observed;
- observation count;
- latest observed status;
- whether any terminal state was observed;
- timestamp of the latest terminal observation;
- final score from the latest terminal observation when available.

The catalog deliberately preserves terminal evidence even if a later malformed/non-terminal observation appears; it does not let a later weak observation erase an already observed FT/AET/PEN state.

## Governance

- Provider calls: **0**.
- `fixture_history_snapshots.csv` remains the historical source-of-truth.
- `historical_fixtures.csv` is a rebuildable `DERIVED_WAREHOUSE` projection registered in Stage80 Archive Manifest.
- No rows are fabricated before PBK observed a fixture.
- Invalid source rows without `fixture_id` or `observed_at_utc` are rejected and make the projection `ATTENTION`.
- A missing history source yields a header-only catalog plus `WAITING_SOURCE`; this is bootstrapping, not fake completeness.
- The layer never creates signals and cannot mutate probability, EV, R1/R2/R3 eligibility, stake, settlement or Forward journal.

## Reschedule meaning

`reschedule_observed=YES` means PBK historical evidence contains more than one distinct kickoff timestamp for that fixture. It does **not** infer why the kickoff changed.
