# PBK Stage 62 — O/U 2.5 Market-Movement Preregistration

Date: 2026-09-11  
Status: **PREREGISTERED BEFORE TEST INSPECTION**

## Purpose

Test whether movement between the first available Bet365 Over/Under 2.5 market and Bet365 closing O/U 2.5 market contains a stable betting signal in the four non-Italian Big-5 leagues.

This is intentionally different from Stage 8. Stage 8 tested unconditional O/U and recent-form/goal filters. Stage 62 tests only market movement.

## Data and split

- Canonical source: `Football_Top5_2016-2026.csv`
- Require a complete Bet365 first O/U 2.5 pair and complete Bet365 closing O/U 2.5 pair for the same match.
- Leagues: Premier League, La Liga, Bundesliga, Ligue 1.
- TRAIN: 2019/20–2022/23.
- TEST: 2023/24–2025/26.
- Flat 1u.
- Historical bet price: Bet365 closing price for the selected side.
- Pushes are impossible on 2.5; settlement is win/loss only.

## Probability normalization

For first and closing O/U pairs separately:

- raw implied Over = `1 / over_odds`
- raw implied Under = `1 / under_odds`
- no-vig Over = raw Over / (raw Over + raw Under)
- no-vig Under = 1 - no-vig Over

Movement is closing no-vig probability minus first no-vig probability.

## Primary hypotheses

Exactly two primary rules are tested per league.

### O1 — Over Steam

- `close_no_vig_over - first_no_vig_over >= +0.03`
- bet **Over 2.5** at Bet365 closing odds.

### O2 — Under Steam

- `close_no_vig_under - first_no_vig_under >= +0.03`
- equivalently `close_no_vig_over - first_no_vig_over <= -0.03`
- bet **Under 2.5** at Bet365 closing odds.

No goal/form/table/team/odds-range filter is allowed in the primary rules.

## Candidate / watch pass criteria

A league×rule may be promoted only to a **FORWARD-WATCH candidate**, not a canonical betting rule, if all are true:

1. TRAIN bets >= 100.
2. TEST bets >= 75.
3. TRAIN ROI > 0%.
4. TEST ROI > 0%.
5. At least 2 of 3 TEST seasons have positive ROI.
6. Nearby threshold stress at +/−0.02 and +/−0.04 does not reverse the TEST sign at both neighboring thresholds.

Statistical one-sided p-values and Benjamini-Hochberg q-values across the 8 primary league×rule tests will be reported, but are diagnostic rather than sufficient on their own.

## Stress tests fixed in advance

For each primary rule:

- movement threshold 0.02
- movement threshold 0.03 — primary
- movement threshold 0.04

No threshold will be re-selected based on TEST ROI.

## Reporting

For each league×rule report:

- TRAIN n / ROI / P&L
- TEST n / ROI / P&L
- TEST season-by-season n / ROI
- average closing odds
- maximum drawdown in units on chronological flat-1u bets
- one-sided p-value and BH q-value
- nearby-threshold TEST results

## Decision boundary

- No Stage 62 historical row enters canonical `ops/forward_log.csv`.
- No R4/R5 is created directly from this historical study.
- A passing result becomes a named **O/U market-movement WATCH** only and must accumulate prospective evidence.
- Existing R1/R2/R3 and Stage61 market-steam watch remain unchanged.
