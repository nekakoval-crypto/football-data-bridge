# Stage71D — Ф(0) / Draw No Bet market-movement results

Date: 2026-09-11
Preregistration: `research/stage71d_dnb_market_movement_prereg_2026-09-11.md`
Canonical source: `Football_Top5_2016-2026.csv`
Status: **INSUFFICIENT_SAMPLE / NO FORWARD WATCH CANDIDATE**

## Data audit

Eligible historical market rows require `AHh=0`, `AHCh=0` and complete Bet365 open/close home+away AH prices. Stable zero-line rows before the movement filter:

| League | TRAIN 2019/20–2022/23 | TEST 2023/24–2025/26 |
|---|---:|---:|
| Premier League | 108 | 73 |
| La Liga | 145 | 91 |
| Serie A | 109 | 100 |
| Bundesliga | 80 | 66 |
| Ligue 1 | 127 | 54 |

These are real AH=0 / DNB prices, not synthetic prices inferred from 1X2.

## Primary threshold: +3 percentage points no-vig steam

| League | Selection | TRAIN n | TRAIN ROI | TEST n | TEST P/L | TEST ROI | TEST MDD | p one-sided | BH q |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Premier League | Ф1(0) | 10 | +4.50% | 6 | +0.53u | +8.83% | 1.00u | 0.377 | 0.729 |
| Premier League | Ф2(0) | 20 | -14.40% | 16 | -4.17u | -26.06% | 4.17u | 0.891 | 0.891 |
| La Liga | Ф1(0) | 23 | -20.22% | 20 | +1.53u | +7.65% | 3.00u | 0.337 | 0.729 |
| La Liga | Ф2(0) | 21 | -21.00% | 9 | +0.49u | +5.44% | 2.00u | 0.437 | 0.729 |
| Serie A | Ф1(0) | 12 | +0.17% | 15 | -1.73u | -11.53% | 3.00u | 0.724 | 0.891 |
| Serie A | Ф2(0) | 10 | -15.10% | 9 | -2.35u | -26.11% | 4.00u | 0.830 | 0.891 |
| Bundesliga | Ф1(0) | 20 | +42.50% | 14 | +1.22u | +8.71% | 1.12u | 0.326 | 0.729 |
| Bundesliga | Ф2(0) | 9 | +58.44% | 7 | +0.49u | +7.00% | 2.00u | 0.414 | 0.729 |
| Ligue 1 | Ф1(0) | 19 | -29.00% | 8 | -0.62u | -7.75% | 2.00u | 0.600 | 0.857 |
| Ligue 1 | Ф2(0) | 25 | -23.40% | 12 | +2.74u | +22.83% | 2.00u | 0.173 | 0.729 |

The preregistered candidate gate requires TEST n >= 60 **after the movement condition**. Every primary hypothesis fails that gate; the largest TEST sample is only 20.

## Nearby-threshold stress on TEST

| League | Selection | +2pp n / ROI | +3pp n / ROI | +4pp n / ROI |
|---|---|---|---|---|
| Premier League | Ф1(0) | 11 / -6.82% | 6 / +8.83% | 4 / +38.25% |
| Premier League | Ф2(0) | 23 / -6.48% | 16 / -26.06% | 7 / +30.43% |
| La Liga | Ф1(0) | 27 / +0.48% | 20 / +7.65% | 12 / +9.08% |
| La Liga | Ф2(0) | 13 / -13.08% | 9 / +5.44% | 5 / +51.40% |
| Serie A | Ф1(0) | 24 / +3.33% | 15 / -11.53% | 11 / +11.55% |
| Serie A | Ф2(0) | 17 / -33.18% | 9 / -26.11% | 8 / -16.88% |
| Bundesliga | Ф1(0) | 20 / +8.95% | 14 / +8.71% | 9 / +5.22% |
| Bundesliga | Ф2(0) | 10 / +11.40% | 7 / +7.00% | 2 / -11.00% |
| Ligue 1 | Ф1(0) | 12 / -5.33% | 8 / -7.75% | 4 / +14.50% |
| Ligue 1 | Ф2(0) | 18 / -1.83% | 12 / +22.83% | 8 / +3.88% |

## Season check for the visually strongest primary result

Bundesliga Ф1(0), +3pp:
- 2023/24: +40.25%
- 2024/25: -13.50%
- 2025/26: -1.50%

So even this superficially attractive row has only 14 TEST bets and fails the preregistered 2-of-3 positive-season condition.

## Statistical note

The reported one-sided p-values are one-sample tests of per-bet profit > 0 on the TEST sample; BH q-values correct across the 10 preregistered league×direction primary tests. No primary result is statistically convincing, and all samples are far below the practical n gate.

## Decision

- **No Stage71D strategy.**
- **No Stage71D WATCH candidate.**
- Do not lower the n>=60 gate after seeing these results.
- Do not widen the movement condition or add form/favorite/odds filters to rescue a row.
- Historical AH=0 remains useful as genuine DNB data, but a steam strategy at +3pp is too sparse to justify promotion.

Next: Double Chance (1Х / Х2 / 12) must be treated separately. The canonical historical file has no direct Double Chance bookmaker-price columns, so any operational Double Chance research should use prospective real-market capture rather than synthetic 1X2-derived execution prices.
