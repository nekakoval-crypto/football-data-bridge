# PBK Stage 71B — 1X2 Open-Odds Discovery Preregistration

Date locked: 2026-09-11
Status: PREREGISTERED BEFORE TEST

## Why
The canonical R1/R2 price band 1.20 <= odds < 2.10 belongs only to those rules. PBK must not impose that range, or any global maximum odds, on the full system. A future strategy may legitimately target a side priced 2.34, 3.50, 4.40 or higher if independent evidence supports it.

## Global rule
There is NO global maximum odds cap in PBK. Odds restrictions are strategy-level parameters only.

## Historical dataset / split
Dataset: canonical Football_Top5_2016-2026.csv.
Primary comparable market window: seasons 2019/20–2025/26, Bet365 first 1X2 snapshot when complete.
TRAIN: 2019/20–2022/23.
TEST: 2023/24–2025/26.
Flat 1u historical measurement at the selected Bet365 first price. This is discovery research only and cannot create a canonical rule directly.

## Pre-specified selections
Evaluate team-side 1X2 selections independently:
- HOME: П1 at B365H.
- AWAY: П2 at B365A.

Also classify each selected team at the captured snapshot as:
- FAVORITE: its odds are the unique lowest of B365H/B365D/B365A.
- NON_FAVORITE: it is not the unique lowest price.

This deliberately permits underdog/team prices such as 4.40; they are not forced into a favorite strategy family.

## Pre-specified odds buckets
Buckets are descriptive discovery partitions, locked before TEST:
- 1.20 <= odds < 1.50
- 1.50 <= odds < 1.80
- 1.80 <= odds < 2.10
- 2.10 <= odds < 3.00
- 3.00 <= odds < 4.00
- 4.00 <= odds < 6.00
- odds >= 6.00

There is no upper bound on the last bucket.

## Outputs
For side × favorite-status × odds-bucket report:
- TRAIN bets, P/L, ROI;
- TEST bets, P/L, ROI;
- TEST season-by-season sign where sample exists;
- observed chronological TEST max drawdown;
- average odds.

## Candidate gate
This exploratory bucket screen is deliberately strict because many cells are being inspected. A bucket can only become a named FOLLOW-UP CANDIDATE if all are true:
1. TRAIN n >= 150;
2. TEST n >= 100;
3. TRAIN ROI > 0;
4. TEST ROI > 0;
5. at least 2 of 3 TEST seasons have positive ROI where each season has >=20 bets;
6. no post-result change to side, odds bucket or favorite-status definition.

Even then it is NOT an R-rule. It requires a new preregistration with a fresh hypothesis / holdout or prospective collection.

## Interpretation guardrails
- A high price is not value by itself.
- A match omitted by R1/R2 is not omitted by PBK as a whole.
- Do not widen R1/R2 from 2.10 based on this analysis; any successful higher-price family is separate.
- Do not convert a winning 4.40 underdog after the fact into a strategy.
