# PBK Stage 71B — 1X2 Open-Odds Discovery Results

Preregistration: `research/stage71b_1x2_open_odds_prereg_2026-09-11.md`
Dataset: Football_Top5_2016-2026.csv; complete Bet365 first 1X2; TRAIN 2019/20–2022/23; TEST 2023/24–2025/26.

## Result

**No pre-specified side × favorite-status × odds bucket passes the Stage71B candidate gate.**

This means the system should NOT widen R1/R2 or create a generic high-odds strategy from odds alone. It does NOT mean prices above 2.10/3.00/4.00 are forbidden: they remain visible to discovery and may be used by a future strategy with independent predictive logic.

| Selection | Status | Odds bucket | TRAIN n | TRAIN ROI | TEST n | TEST ROI | TEST P/L | TEST MDD | Positive TEST seasons* |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| П2 | FAVORITE | 1.20-1.50 | 331 | -2.53% | 184 | +5.09% | +9.36u | 3.87u | 3/3 |
| П2 | FAVORITE | 1.50-1.80 | 545 | -3.72% | 415 | -0.07% | -0.28u | 14.15u | 1/3 |
| П2 | FAVORITE | 1.80-2.10 | 527 | -4.09% | 390 | +2.17% | +8.45u | 19.31u | 2/3 |
| П2 | FAVORITE | 2.10-3.00 | 1138 | -1.08% | 783 | +1.14% | +8.96u | 24.82u | 2/3 |
| П2 | NON_FAVORITE | 2.10-3.00 | 545 | -12.66% | 426 | -4.10% | -17.48u | 45.77u | 1/3 |
| П2 | NON_FAVORITE | 3.00-4.00 | 1432 | -4.58% | 1037 | -10.79% | -111.90u | 145.60u | 0/3 |
| П2 | NON_FAVORITE | 4.00-6.00 | 1271 | -5.42% | 1034 | -11.08% | -114.61u | 129.47u | 1/3 |
| П2 | NON_FAVORITE | 6.00+ | 1381 | -5.05% | 977 | -29.61% | -289.25u | 316.25u | 0/3 |
| П1 | FAVORITE | 1.20-1.50 | 889 | -3.02% | 714 | -0.70% | -4.97u | 20.90u | 1/3 |
| П1 | FAVORITE | 1.50-1.80 | 1033 | -3.76% | 785 | -6.19% | -48.60u | 60.50u | 0/3 |
| П1 | FAVORITE | 1.80-2.10 | 978 | -8.23% | 701 | -6.64% | -46.52u | 55.38u | 0/3 |
| П1 | FAVORITE | 2.10-3.00 | 1477 | -4.25% | 1097 | -6.79% | -74.46u | 84.93u | 1/3 |
| П1 | NON_FAVORITE | 2.10-3.00 | 525 | -10.97% | 406 | -10.62% | -43.13u | 48.64u | 0/3 |
| П1 | NON_FAVORITE | 3.00-4.00 | 951 | -12.63% | 663 | -17.33% | -114.90u | 119.75u | 0/3 |
| П1 | NON_FAVORITE | 4.00-6.00 | 674 | -5.12% | 526 | -21.77% | -114.50u | 131.78u | 0/3 |
| П1 | NON_FAVORITE | 6.00+ | 471 | -1.96% | 252 | -55.16% | -139.00u | 139.00u | 0/3 |

* Season counts only seasons with at least 20 bets in that cell.

## Interpretation

- The 1.20–2.10 range stays locked inside R1/R2; this screen gives no reason to widen those canonical rules.
- There is no global PBK odds ceiling. A 4.40 side is allowed to enter future research if another pre-specified strategy selects it.
- High odds alone are not evidence of value. In this broad Big-5 screen the 4.00–6.00 and 6.00+ non-favorite buckets are materially negative in TEST.
- A match can be rejected by R1/R2 and still remain visible to other strategies/WATCH/research layers.
