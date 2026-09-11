# PBK Stage 62 — O/U 2.5 Market-Movement Results

Date: 2026-09-11  
Status: **COMPLETE — ONE FORWARD-WATCH CANDIDATE, NO CANONICAL RULE**

Preregistration: `research/stage62_ou25_market_movement_prereg_2026-09-11.md`

## Data

- Canonical `Football_Top5_2016-2026.csv`
- Bet365 first + closing O/U 2.5 pair required
- TRAIN: 2019/20–2022/23
- TEST: 2023/24–2025/26
- Leagues: Premier League, La Liga, Bundesliga, Ligue 1
- Flat 1u
- Historical execution: Bet365 closing O/U 2.5 price
- Movement: normalized no-vig probability change from first to close
- Primary threshold: 3 percentage points

## Primary results

| League | Rule | TRAIN n | TRAIN ROI | TEST n | TEST ROI | TEST P/L u | + TEST seasons | Avg close | TEST MDD u | one-sided p | BH q | Prereg pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Premier League | O1 Over Steam | 178 | -8.06% | 142 | -7.44% | -10.56 | 0/3 | 1.561 | 14.25 | 0.872 | 0.872 | NO |
| Premier League | O2 Under Steam | 229 | -15.02% | 184 | +3.72% | +6.84 | 2/3 | 2.052 | 9.75 | 0.313 | 0.872 | NO — TRAIN/stress |
| La Liga | O1 Over Steam | 240 | -6.60% | 160 | +2.12% | +3.40 | 2/3 | 1.779 | 7.90 | 0.380 | 0.872 | NO — TRAIN |
| La Liga | O2 Under Steam | 297 | -4.77% | 221 | -6.00% | -13.27 | 1/3 | 1.726 | 21.70 | 0.845 | 0.872 | NO |
| **Bundesliga** | **O1 Over Steam** | **170** | **+0.05%** | **148** | **+2.36%** | **+3.49** | **2/3** | **1.506** | **8.58** | **0.340** | **0.872** | **PASS → WATCH ONLY** |
| Bundesliga | O2 Under Steam | 237 | -7.32% | 149 | -9.41% | -14.02 | 1/3 | 2.174 | 20.49 | 0.858 | 0.872 | NO |
| Ligue 1 | O1 Over Steam | 228 | -0.71% | 147 | -1.20% | -1.77 | 2/3 | 1.610 | 11.25 | 0.574 | 0.872 | NO |
| Ligue 1 | O2 Under Steam | 239 | -5.41% | 171 | -4.41% | -7.54 | 2/3 | 1.907 | 22.10 | 0.730 | 0.872 | NO |

## Bundesliga O1 robustness

Preregistered rule:

- Bet365 first and close O/U 2.5 pair available.
- `close_no_vig_over - first_no_vig_over >= +0.03`.
- Bet Over 2.5 at Bet365 close.

### TEST by season

| Season | Bets | ROI | Profit u |
|---|---:|---:|---:|
| 2023/24 | 41 | +13.88% | +5.69 |
| 2024/25 | 51 | -9.06% | -4.62 |
| 2025/26 | 56 | +4.32% | +2.42 |

### Nearby-threshold stress — TEST only

| Over probability increase | Bets | ROI | Profit u |
|---|---:|---:|---:|
| +0.02 | 203 | +5.40% | +10.97 |
| **+0.03 preregistered** | **148** | **+2.36%** | **+3.49** |
| +0.04 | 82 | +14.38% | +11.79 |

The TEST sign stays positive at both neighboring thresholds. Threshold 0.03 remains the only primary definition and is not re-selected from TEST.

## Interpretation

The Bundesliga O1 candidate satisfies every preregistered practical watch criterion, but the evidence is weak:

- TRAIN is only barely positive (+0.05%).
- TEST ROI is modest (+2.36%).
- 2024/25 is negative.
- raw one-sided TEST p ≈ 0.340.
- BH q ≈ 0.872 across the 8 primary league×rule tests.

Therefore this is not a proven betting edge and must not become an automatic canonical rule from historical data alone.

## Decision

- Create **Stage62 Bundesliga O/U Over-Steam WATCH** only.
- Freeze the first complete Bet365 O/U 2.5 pair prospectively.
- Track timestamped Bet365 O/U 2.5 snapshots toward kickoff.
- Record first crossing of +3 pp in no-vig Over probability.
- Record Marathonbet Over 2.5 price at crossing when available.
- Freeze the last observed pre-kickoff Bet365 O/U pair separately and classify whether historical O1 was actually satisfied at observed close.
- Do not insert historical rows into canonical `ops/forward_log.csv`.
- Existing R1/R2/R3 and Stage61 stay unchanged.
