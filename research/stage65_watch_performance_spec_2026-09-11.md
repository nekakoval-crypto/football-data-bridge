# PBK Stage 65 — Prospective WATCH Performance Specification

Date: 2026-09-11  
Status: OPERATIONAL SPEC — NO NEW BETTING RULE

## Purpose

Measure the real prospective performance of research WATCH events without choosing a different market after the event.

Stage65 consumes only WATCH events that were actually recorded prospectively by:

- Stage61 — Premier League favorite steam (П1/П2)
- Stage62 — Bundesliga ТБ(2.5) steam
- Stage63 — Big-5 ОЗ — Да / ОЗ — Нет market movement

Stage65 never writes to canonical `forward_log.csv`, never promotes a WATCH to an R-rule, and never substitutes an alternative market (team total, handicap, BTTS, etc.) after seeing the match result.

## Execution convention

For every first-crossing event:

- stake = flat 1u for measurement only;
- primary executable price = Marathonbet price captured at the first crossing;
- Bet365 crossing price is retained as a market-reference comparison;
- if Marathonbet price was not observed at the crossing, the event stays in the WATCH sample but is excluded from user-executable P/L and ROI;
- crossing fields are immutable after ingestion.

This is paper research only and is not evidence that a real-money bet was placed.

## Settlement

League matches settle from API-Football final full-time score.

- Stage61: recorded opening favorite at crossing — П1 if `H`, П2 if `A`.
- Stage62: ТБ(2.5).
- Stage63: recorded direction — ОЗ — Да or ОЗ — Нет.
- `FT` settles normally.
- cancelled fixture -> VOID.
- abandoned / awarded / walkover -> REVIEW, no automatic P/L.
- postponed / not started -> remains pending under the same API fixture id.

## Close persistence

Stage65 distinguishes two questions:

1. **First-crossing performance** — what would have happened if the first observed crossing were acted on immediately at the captured Marathonbet price?
2. **Close-qualified subset** — among those first crossings, which still satisfied the original WATCH condition at the latest observed pre-kickoff close?

A crossing that later loses qualification is marked `REVERTED_AT_CLOSE` rather than deleted.

## Outputs

- `ops/stage65_watch_ledger.csv` — one row per prospectively recorded crossing.
- `ops/watch_performance.json`
- `ops/watch_performance.md`
- `ops/stage65_last_run.json`

The report contains overall and per-family metrics:

- crossings / settled / pending;
- Marathonbet execution coverage;
- W-L, P/L and ROI at first crossing;
- close-observed / close-qualified / reverted counts;
- close-persistence rate;
- separate P/L and ROI for close-qualified and reverted subsets;
- observed maximum drawdown on executable settled crossing bets.

ROI is `N/A` until at least one executable event is settled. Historical backfill before each WATCH stage began is forbidden.
