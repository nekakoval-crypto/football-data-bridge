# Stage80 — Football-Data.co.uk Top-5 nine-season historical source

Status: **HISTORICAL BACKFILL SOURCE + DURABLE RESEARCH PROJECTION**

PBK needs a separate historical-research layer that must never be confused with forward validation. This slice builds a reproducible 9-season Top-5 archive package from Football-Data.co.uk.

## Scope

Previous 9 completed seasons:

- 2017/18
- 2018/19
- 2019/20
- 2020/21
- 2021/22
- 2022/23
- 2023/24
- 2024/25
- 2025/26

Top-5 leagues:

- England Premier League — E0
- Germany Bundesliga — D1
- Italy Serie A — I1
- Spain La Liga — SP1
- France Ligue 1 — F1

The source matrix is therefore exactly **45 league-season CSV files**.

## Output

The workflow publishes two 90-day build artifacts:

- `football-data-top5-9seasons-source` — original downloaded CSVs;
- `football-data-top5-9seasons` — normalized combined CSV, metadata, source checksums, referee research and pre-match context research.

On successful `main` builds it also persists compact/rebuildable research outputs into `ops/`:

- `ops/epl_referee_profiles_research.csv`;
- `ops/epl_referee_team_splits_research.csv`;
- `ops/stage80_referee_research_last_run.json`;
- `ops/top5_prematch_context_research.csv`;
- `ops/stage80_prematch_context_last_run.json`.

The durable pre-match projection is registered in the Stage80 archive manifest and readiness telemetry. It remains research-only and does not become operational betting authority by being persisted.

The normalized row includes:

- deterministic historical match identity;
- source URL/file/season/league provenance;
- full-time and half-time result;
- referee name where the source provides it;
- shots, shots on target, fouls, corners and cards where the source provides them;
- selected opening 1X2, total 2.5 and Asian-handicap market fields where available;
- selected closing 1X2, total 2.5 and Asian-handicap fields where available, preserving open/close separation for later market-movement research;
- explicit research/backfill flags.

Missing columns remain empty. PBK does not zero-fill unavailable historical metrics.

## Referee coverage

The workflow measures referee coverage from the exact 45-file source matrix and materializes an explicit `football_data_epl_referee_matches.csv` slice.

For the current 2017/18–2025/26 source package:

- Premier League (`E0`): **3420 / 3420** matches have `Referee`;
- Bundesliga, Serie A, La Liga and Ligue 1 source CSVs do not expose the `Referee` column in this matrix;
- total Top-5 referee coverage is therefore **3420 / 16111 = 21.23%**.

PBK labels this historical referee slice **EPL_ONLY**. It must never be described as complete Top-5 referee history, and missing referee data for the other leagues is UNKNOWN rather than inferred.

### Referee research projections

From the EPL-only slice the workflow also derives two research-only CSVs:

- `football_data_epl_referee_profiles.csv` — one row per referee with match count, season span, home/draw/away result rates, goals, yellow/red cards and fouls where observed;
- `football_data_epl_referee_team_splits.csv` — one row per referee+team pair with the team's observed W/D/L, points, goals, cards and fouls under that referee.

These are descriptive historical aggregates only. PBK does **not** label an observed split as referee bias or causation. Small samples must remain visibly small, missing metrics stay UNKNOWN, and no minimum-sample rule is converted into betting authority here.

The Football-Data matrix used here does not provide a penalty field, so penalty counts are explicitly marked unavailable rather than inferred from goals, cards, events or other proxies.

## Historical pre-match context research

The normalized 16,111-match Top-5 matrix also produces `football_data_top5_prematch_context.csv`; after a successful `main` build the verified projection is persisted as `ops/top5_prematch_context_research.csv` with `ops/stage80_prematch_context_last_run.json`.

For each match this projection records only information available from **strictly earlier calendar dates** in the same league-season:

- weekday and source-local kickoff time where available;
- Monday / Thursday / weekend flags;
- team rest days;
- number of prior matches in the previous 7 and 14 days;
- short-rest flags;
- pre-match played, points, goals for/against, goal difference and points-per-game;
- conservative pre-match table rank;
- rolling all-venue form over the previous 5 and 10 matches;
- rolling home-only form for the home team and away-only form for the away team.

### No-lookahead rule

Matches on the same calendar date are projected as one group. PBK calculates all pre-match rows for that date **before** applying any result from that date to team state.

This is deliberately conservative: when historical kickoff ordering is missing or uncertain, an earlier match on the same day is not allowed to leak its result into a later row.

The projection is research/backfill only. It does not become a validated probability feature or current operational signal merely because it exists.

## Separation from forward evidence

This dataset is explicitly:

- `historical_backfill_only = true`;
- `forward_validation_input = false`;
- not current operational authority;
- not a PBK probability source by itself;
- unable to mutate R1/R2/R3 eligibility, EV/value, stakes, settlement or Forward.

Future historical model research may consume it in a clearly separate training/backtest contour, but forward-validation ledgers must remain timestamped forward-only evidence.

## Provenance note

Football-Data.co.uk states that its CSV data is free and provides historical season downloads and a notes file describing source/column conventions. PBK keeps per-file URL and SHA-256 evidence in the artifact metadata. Any later redistribution or public-product use should still re-check the source's then-current terms and attribution requirements.
