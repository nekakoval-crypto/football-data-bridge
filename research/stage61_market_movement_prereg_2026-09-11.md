# PBK Stage 61 — Market-Movement Hypotheses (Preregistration)

Date: 2026-09-11
Status: PREREGISTERED BEFORE TEST INSPECTION

## Goal

Search for a genuinely separate strategy family for the four non-Italian Big-5 leagues without transferring Serie A R1/R2 and without a broad post-hoc grid.

Leagues:
- Premier League
- La Liga
- Bundesliga
- Ligue 1

## Data and split

- Source: canonical `Football_Top5_2016-2026.csv`
- Require complete Bet365 first and closing 1X2 prices (`B365H/D/A`, `B365CH/CD/CA`)
- TRAIN: 2019/20–2022/23
- TEST: 2023/24–2025/26
- Bet settlement: final 90-minute 1X2 result (`FTR`)
- Stake: flat 1u
- Execution price for all Stage61 tests: Bet365 closing price

## Probability transform

For both first and close, convert H/D/A odds to normalized no-vig implied probabilities:

`p_i = (1/odds_i) / sum_j(1/odds_j)`

Movement is `close_no_vig_probability - first_no_vig_probability`, measured in absolute probability points.

## Preregistered rules

Threshold is fixed at **3 percentage points (0.03)**. It will not be tuned after TEST is inspected.

### M1 — Favorite Steam

- Determine unique opening favorite from first Bet365 1X2 odds.
- The same side remains unique favorite at close.
- Its no-vig probability increases by at least +0.03.
- Bet that favorite at Bet365 close.

Hypothesis: meaningful late market confirmation may contain residual information even after repricing.

### M2 — Favorite Drift Contrarian

- Determine unique opening favorite.
- The same side remains unique favorite at close.
- Its no-vig probability decreases by at least −0.03.
- Bet that favorite at Bet365 close.

Hypothesis: strong late drift may sometimes over-discount the original favorite, creating a better executable price.

### M3 — Favorite Flip

- Opening and closing unique favorites are different teams.
- Bet the new closing favorite at Bet365 close.

Hypothesis: a true favorite reversal may capture large information updates rather than ordinary noise.

### M4 — Draw Steam

- Draw no-vig probability increases by at least +0.03 from first to close.
- Bet Draw at Bet365 close.

Hypothesis: late movement toward parity may identify matches where draw probability was initially underpriced.

## Promotion discipline

A league×rule result is **not** promoted to a live rule merely because aggregate ROI is positive.

Minimum historical candidate requirements:
1. TRAIN ROI > 0.
2. TEST ROI > 0.
3. At least 60 TEST bets.
4. At least 2 of 3 TEST seasons individually positive.
5. Nearby-threshold stress at 0.02 and 0.04 must keep the same TEST ROI sign; these are robustness checks only, never used to select a better threshold.
6. Report maximum drawdown and average closing odds.
7. No R4/R5 is created unless the preregistered 0.03 rule passes the above conditions.

## Multiple-testing note

There are exactly 16 primary league×rule tests (4 leagues × 4 rules). Report raw one-sided mean-return p-values and Benjamini-Hochberg q-values across the 16 primary TEST results. Statistical correction is diagnostic; forward validation remains decisive for any candidate.

## Boundary

This stage is research only. Existing R1/R2/R3 and canonical forward rows remain unchanged.