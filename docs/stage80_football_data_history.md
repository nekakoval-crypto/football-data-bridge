# Stage80 — Football-Data.co.uk Top-5 nine-season historical source

Status: **HISTORICAL BACKFILL SOURCE — ARTIFACT ONLY**

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

The workflow publishes two 90-day artifacts:

- `football-data-top5-9seasons-source` — original downloaded CSVs;
- `football-data-top5-9seasons` — normalized combined CSV, metadata, and source checksums.

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
