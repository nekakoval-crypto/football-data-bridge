# PBK — Fixed R1/R2 Cross-League Audit

Date: 2026-09-11  
Status: **RESEARCH ONLY — NO NEW LIVE RULE**

## Purpose

Answer whether the currently locked Serie A R1/R2 pattern can be transferred unchanged to the other Big-5 leagues.

No odds bands, form thresholds, leagues, or seasons were optimized in this audit. The exact locked definitions were applied mechanically to every league.

## Source and split

- Canonical source: `Football_Top5_2016-2026.csv`
- Seasons: 2016/17–2025/26
- TRAIN: 2016/17–2021/22 (6 seasons)
- TEST: 2022/23–2025/26 (4 seasons)
- Stake: flat 1u
- Price: Bet365 first available 1X2 snapshot (`B365*`)

The split is the same split that reproduces the locked R2 result exactly:
- Serie A R2 TRAIN: 397 bets, ROI +7.23%
- Serie A R2 TEST: 236 bets, ROI +9.10%

## Exact definitions

### R1 analogue

- Away is the unique lowest Bet365 1X2 price (`B365A < B365H` and `B365A < B365D`)
- `1.20 <= B365A < 2.10`
- Bet Away win
- flat 1u

### R2 analogue

- R1 analogue
- both teams have at least 5 prior current-season league matches
- away last-5 league PPG > home last-5 league PPG
- Bet Away win
- flat 1u

## R1 results — exact fixed rule

| League | TRAIN bets | TRAIN ROI | TEST bets | TEST ROI | ALL bets | ALL ROI | Positive seasons |
|---|---:|---:|---:|---:|---:|---:|---:|
| Premier League | 498 | +0.33% | 328 | -5.58% | 826 | -2.02% | 4/10 |
| La Liga | 342 | -5.56% | 210 | +0.11% | 552 | -3.41% | 4/10 |
| Bundesliga | 341 | -10.87% | 203 | -5.90% | 544 | -9.01% | 3/10 |
| **Serie A** | **527** | **+6.85%** | **321** | **+6.13%** | **848** | **+6.58%** | **8/10** |
| Ligue 1 | 288 | -3.53% | 259 | -3.81% | 547 | -3.67% | 3/10 |

## R2 results — exact fixed rule

| League | TRAIN bets | TRAIN ROI | TEST bets | TEST ROI | ALL bets | ALL ROI | Positive seasons |
|---|---:|---:|---:|---:|---:|---:|---:|
| Premier League | 368 | -0.43% | 237 | -8.73% | 605 | -3.69% | 2/10 |
| La Liga | 260 | -5.46% | 158 | -7.44% | 418 | -6.21% | 3/10 |
| Bundesliga | 238 | -10.93% | 151 | -4.23% | 389 | -8.33% | 4/10 |
| **Serie A** | **397** | **+7.23%** | **236** | **+9.10%** | **633** | **+7.93%** | **8/10** |
| Ligue 1 | 228 | -2.83% | 191 | -6.07% | 419 | -4.31% | 4/10 |

## Interpretation

1. **Do not extend R1 or R2 mechanically outside Serie A.**
2. Serie A is the only Big-5 league where the exact fixed R1 definition is positive in both TRAIN and TEST.
3. Serie A is also the only league where the exact fixed R2 definition is clearly positive in both TRAIN and TEST.
4. La Liga R1 TEST is essentially flat (+0.11%) after a negative TRAIN (-5.56%); this is not evidence of an edge.
5. Bundesliga R2 improves from strongly negative TRAIN to mildly negative TEST, but still does not qualify.
6. The audit therefore confirms that the current live scope of R1/R2 being Serie A-only is evidence-based rather than an infrastructure limitation.

## Decision

- R1: **UNCHANGED — Serie A only**
- R2: **UNCHANGED — Serie A only**
- R3: **UNCHANGED — Big-5 prospective rule**
- No R4/R5 is created from this audit.

Any future rule for England, Spain, Germany, or France must be researched as a new pre-specified hypothesis and validated separately; it must not be presented as a transferred version of R1/R2 merely because the infrastructure supports all Big-5 leagues.
