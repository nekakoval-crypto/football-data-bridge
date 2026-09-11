# Stage71H — Core Market Data Readiness Policy

Locked before the first readiness-board run.

## Purpose
Stage71H is governance, not strategy discovery. It answers whether each PBK core market family has enough auditable prospective market history to permit a *separate* discovery freeze and future preregistration. It never creates a bet, WATCH or R-rule.

## Core universe
The board covers exactly the eight families in `config/pbk_core_market_registry.json`.

## Data-readiness gate for raw prospective collection families
For TEAM_TOTAL, DOUBLE_CHANCE, EUROPEAN_HANDICAP and DRAW_NO_BET, `DISCOVERY_POOL_READY` requires all of:
1. At least 120 unique fixtures with a frozen observed pre-kickoff close.
2. Marathonbet close-price coverage on at least 90% of those closed fixtures (at least one executable selection on the relevant market family).
3. Result/settlement coverage on at least 90% of those closed fixtures.
4. No signal leakage from the raw capture (`signals_created = 0`).
5. Market identity guardrails remain valid.

The 120-fixture floor is only permission to freeze a discovery pool. It is not evidence of edge, not a TEST sample and not permission to bet. Any hypothesis selected from the discovery pool must be preregistered and evaluated on a new independent future holdout. League-, line- or side-specific hypotheses may require substantially more data than this family-level floor.

## Other family statuses
- MATCH_RESULT_1X2: governed by existing canonical/challenger framework, not Stage71H discovery readiness.
- MATCH_TOTAL: governed by existing Stage62 WATCH framework unless a new independent hypothesis is preregistered.
- BTTS: governed by Stage63/65/69 discovery/WATCH framework; no direct promotion from discovery data.
- ASIAN_HANDICAP: Stage64 historical hypotheses remain rejected; a new path requires an independent hypothesis or regime-change protocol.

## Readiness states
- `ACTIVE_GOVERNED`: an existing canonical/challenger framework owns the family.
- `WATCH_GOVERNED`: an existing WATCH/promotion framework owns the family.
- `HISTORICAL_NO_CANDIDATE`: historical preregistered hypotheses failed; no active raw discovery pool is being promoted.
- `COLLECTING_OPENERS`: feed exists but no closes yet.
- `COLLECTING_CLOSES`: closes exist but fewer than 120 unique fixtures.
- `OUTCOME_LAYER_REQUIRED`: close-price data exists but settlement coverage is below 90%.
- `EXECUTION_COVERAGE_REQUIRED`: Marathonbet close coverage is below 90%.
- `DISCOVERY_POOL_READY`: all family-level data sufficiency gates above pass; this only permits a frozen discovery analysis.

## Anti-overfitting firewall
- Row counts on multi-line markets do not determine readiness; unique fixtures do.
- A single fixture with many ИТБ/ИТМ or European Handicap lines counts once toward the 120-fixture floor.
- Opening/snapshot counts are descriptive only.
- No threshold may be relaxed after seeing results.
- No discovery sample may later be relabeled as its own holdout.
