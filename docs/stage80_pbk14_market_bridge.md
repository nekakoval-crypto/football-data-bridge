# Stage80 PBK14 Historical Market Bridge

## Purpose

This layer extends the historical market-odds research contour from the existing Big-5 baseline toward the locked PBK 16-league universe without changing or weakening the already validated Top-5 pipeline.

Football-Data currently supplies historical results/odds for 14 of the 16 locked PBK leagues. Lithuania (A Lyga) and Latvia (Virsliga) are explicit `NO_FOOTBALL_DATA_HISTORICAL_MARKET_SOURCE` gaps in this contour.

Supported source codes:

- main season-by-season files: E0, SP1, I1, D1, F1, SC0, N1, B1, P1, T1;
- cumulative all-seasons files: AUT, DNK, NOR, POL.

Target season starts are 2017 through 2025.

## Source handling

The source has two different shapes and they are handled explicitly:

1. Main leagues use one CSV per league-season under `mmz4281/<season>/<code>.csv`.
2. Extra leagues use one cumulative CSV per league under `new/<code>.csv`, with a `Season` column.

Both are normalized into the existing Stage80 Football-Data historical schema.

The full normalized Football-Data market file is an ephemeral workflow artifact. It is **not copied into durable `ops/`**. Durable outputs contain only source metadata and the derived identity bridge.

## Identity policy

The bridge never performs silent fuzzy string matching.

Team identity evidence:

- `AUTO`: unique conservative canonical-name equality inside the same league-season;
- `HIGH`: unique schedule+score fingerprint identity. The fingerprint consists of historical `(calendar date, H/A side, goals for, goals against)` observations and requires at least five source matches.

Fixture identity additionally requires:

- same provider league;
- same season start;
- exact calendar date;
- mapped home and away provider team IDs;
- exact final score;
- a unique provider fixture.

Final scores are used only for historical identity resolution. They are never exposed as prematch features and do not give the bridge operational betting authority.

Only `AUTO` and `HIGH` rows are eligible for later historical research joins. `REVIEW` and `UNMAPPED` are fail-closed.

## Durable outputs

- `ops/stage80_football_data_pbk14_history_last_run.json`
- `ops/pbk14_football_data_fixture_bridge.csv`
- `ops/stage80_pbk14_fixture_bridge_last_run.json`

## Governance

This layer is research-only and cannot create or modify:

- PBK probability;
- EV/value;
- R1/R2/R3 eligibility;
- WATCH/promotion state;
- stake;
- Forward journal.

The existing Top-5 historical factor research remains the control baseline until separate descriptive and walk-forward work demonstrates what can be learned from the broader PBK14 bridge.
