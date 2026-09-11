# PBK Stage 61 — Preregistered Market-Movement Results

Date: 2026-09-11  
Status: **COMPLETE — ONE FORWARD-WATCH CANDIDATE, NO CANONICAL R4 YET**

Preregistration: `research/stage61_market_movement_prereg_2026-09-11.md`

## Data

- Canonical `Football_Top5_2016-2026.csv`
- Complete Bet365 first + close 1X2 only
- TRAIN: 2019/20–2022/23
- TEST: 2023/24–2025/26
- Four non-Italian Big-5 leagues
- Flat 1u
- Historical execution price: Bet365 close
- Movement measured in normalized no-vig probability points
- Primary movement threshold fixed before inspection at 0.03

## Primary results

| League | Rule | TRAIN n | TRAIN ROI | TEST n | TEST ROI | TEST P/L u | + TEST seasons | Avg close | TEST MDD u | one-sided p | BH q | Prereg pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Premier League | M1 Favorite Steam | 212 | +0.44% | 166 | **+7.48%** | **+12.42** | **2/3** | 1.733 | 10.29 | 0.128 | 0.699 | **PASS** |
| Premier League | M2 Favorite Drift | 218 | -12.01% | 153 | -5.38% | -8.23 | 1/3 | 1.927 | 11.89 | 0.753 | 0.912 | NO |
| Premier League | M3 Favorite Flip | 43 | -10.79% | 35 | +10.17% | +3.56 | 2/3 | 2.469 | 5.92 | 0.313 | 0.715 | NO — sample |
| Premier League | M4 Draw Steam | 21 | -31.90% | 13 | -26.92% | -3.50 | 1/3 | 4.466 | 7.25 | 0.697 | 0.912 | NO |
| La Liga | M1 Favorite Steam | 271 | -3.42% | 162 | -2.49% | -4.03 | 1/3 | 1.818 | 14.88 | 0.637 | 0.912 | NO |
| La Liga | M2 Favorite Drift | 172 | +0.60% | 135 | -1.25% | -1.69 | 1/3 | 2.001 | 11.36 | 0.558 | 0.912 | NO |
| La Liga | M3 Favorite Flip | 56 | -19.27% | 37 | +11.46% | +4.24 | 2/3 | 2.574 | 5.00 | 0.297 | 0.715 | NO — sample/TRAIN |
| La Liga | M4 Draw Steam | 32 | -16.78% | 25 | -34.80% | -8.70 | 0/3 | 3.536 | 10.10 | 0.896 | 0.956 | NO |
| Bundesliga | M1 Favorite Steam | 180 | -9.89% | 137 | -6.07% | -8.32 | 1/3 | 1.720 | 15.17 | 0.798 | 0.912 | NO |
| Bundesliga | M2 Favorite Drift | 174 | -14.93% | 122 | +6.79% | +8.28 | 2/3 | 1.938 | 8.55 | 0.217 | 0.699 | NO — TRAIN |
| Bundesliga | M3 Favorite Flip | 47 | -9.21% | 43 | +14.95% | +6.43 | 2/3 | 2.475 | 6.02 | 0.218 | 0.699 | NO — sample/TRAIN |
| Bundesliga | M4 Draw Steam | 9 | +163.89% | 7 | +104.71% | +7.33 | 2/3 | 4.247 | 2.00 | 0.161 | 0.699 | NO — tiny sample |
| Ligue 1 | M1 Favorite Steam | 259 | +2.47% | 164 | -20.01% | -32.82 | 0/3 | 1.744 | 32.82 | 0.998 | 0.998 | NO |
| Ligue 1 | M2 Favorite Drift | 181 | +1.71% | 129 | +1.21% | +1.56 | 1/3 | 1.921 | 8.64 | 0.445 | 0.890 | NO — seasons |
| Ligue 1 | M3 Favorite Flip | 54 | -21.26% | 38 | -7.82% | -2.97 | 1/3 | 2.513 | 6.47 | 0.652 | 0.912 | NO |
| Ligue 1 | M4 Draw Steam | 17 | +17.35% | 15 | +84.00% | +12.60 | 2/3 | 4.300 | 4.00 | 0.076 | 0.699 | NO — tiny sample |

## Premier League M1 robustness

Preregistered rule: opening team favorite remains the same closing favorite and its normalized no-vig probability rises by at least 3 percentage points; bet the favorite at B365 close.

### TEST by season

| Season | Bets | ROI | Profit u |
|---|---:|---:|---:|
| 2023/24 | 58 | +25.90% | +15.02 |
| 2024/25 | 62 | +2.85% | +1.77 |
| 2025/26 | 46 | -9.50% | -4.37 |

### Nearby-threshold stress — TEST only

| Steam threshold | Bets | ROI | Profit u | MDD u |
|---|---:|---:|---:|---:|
| +0.02 | 255 | +0.79% | +2.02 | 13.53 |
| **+0.03 preregistered** | **166** | **+7.48%** | **+12.42** | **10.29** |
| +0.04 | 88 | +17.49% | +15.39 | 7.32 |

The nearby thresholds keep the same positive TEST sign, satisfying the preregistered robustness condition. They are not used to re-select a threshold; 0.03 remains the only primary definition.

## Statistical caution

The Premier League M1 candidate is not conventionally significant after accounting for the 16 primary league×rule tests:

- raw one-sided TEST p ≈ 0.128
- Benjamini-Hochberg q ≈ 0.699

Therefore the historical result is **not proof of a stable edge**. The 2025/26 season is also negative. Forward evidence is required.

## Operational timing boundary

Historical M1 eligibility uses the **closing** Bet365 snapshot. A close-defined backtest cannot be honestly converted into an early pre-match betting signal without changing the rule.

Decision:

- Do **not** create a canonical betting R4 yet.
- Create an **R4-WATCH / Market Steam Watch** prospectively.
- Freeze the first complete Bet365 1X2 snapshot for Premier League fixtures.
- Track timestamped Bet365 movement toward kickoff.
- Record the first time +0.03 is crossed, but do not treat that crossing alone as the historical M1 rule.
- Record the final observed pre-kickoff Bet365 snapshot separately.
- Evaluate whether the close-qualified fixture could have been executed at a sufficiently early, still-available Marathonbet price.
- No rows from this historical backtest enter the clean forward ledger.

## Existing strategy decision

- R1 unchanged — Serie A only.
- R2 unchanged — Serie A only.
- R3 unchanged — Big-5 late Monday draw prospective rule.
- Stage61 Premier League M1 = **FORWARD WATCH CANDIDATE**, not a validated live betting rule.