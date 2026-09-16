# PBK Generic 1X2 Probability V1 — preregistration

Date locked: 2026-09-16  
Status: **PREREGISTERED / DATA REQUIRED / RESEARCH ONLY**

## Purpose

Build a symmetric three-outcome probability layer for ordinary Big-5 1X2 matches: П1 / Х / П2. This is separate from canonical R1/R2/R3 and cannot alter their definitions, stakes or authority.

The question is not whether a price bucket was profitable. Stage71B already tested side/favourite/odds buckets and found no pre-specified bucket that passed its candidate gate. This experiment instead asks whether a deliberately simple multiclass calibration can improve Bet365's no-vig probability vector out of sample.

## Historical source and locked split

Canonical source: `Football_Top5_2016-2026.csv`.

Use only Big-5 league rows with complete `B365H`, `B365D`, `B365A` and a settled `FTR` in H/D/A.

- TRAIN: 2019/20, 2020/21, 2021/22, 2022/23.
- TEST: 2023/24, 2024/25, 2025/26.
- TEST must not influence formula, feature set, fit procedure or thresholds.

The source file is not currently stored in GitHub or the connected Drive under the canonical filename. Until it is supplied, status remains `PREREGISTERED_DATA_REQUIRED`; no historical PASS may be claimed.

## M0 — market baseline

For each match, convert complete Bet365 1X2 prices to no-vig probabilities:

`p_market_c = (1 / odds_c) / ((1/H) + (1/D) + (1/A))`

for `c in {H,D,A}`.

These are market-implied probabilities and must never be labelled PBK probability.

## M1 — candidate PBK calibrator

Use one multiclass probability vector, not three unrelated binary models:

`p_pbk_c = softmax(log(p_market_c) + alpha_c)`

Identification lock: `alpha_D = 0`. Fit only `alpha_H` and `alpha_A` on TRAIN by minimizing multiclass log-loss with the deterministic grid-refinement algorithm fixed in `config/pbk_generic_1x2_probability_v1.json`.

Why intentionally simple:
- all three outcomes remain mutually exclusive and probabilities sum to one;
- the market remains the main information source;
- only two fitted parameters reduce overfit risk;
- the result is deterministic and auditable;
- no form/xG/player/context feature can leak into V1 after seeing TEST.

## Locked TEST gate

Generic 1X2 may be labelled historically validated only if every condition passes:

1. TEST has at least 3000 eligible matches.
2. Each of H/D/A occurs at least 300 times in TEST.
3. M1 multiclass Brier score is strictly lower than M0.
4. M1 multiclass log-loss is strictly lower than M0.
5. For every class H/D/A, `abs(mean predicted probability - observed class rate) <= 0.03` on TEST.
6. Every produced probability vector sums to one within `1e-9`.
7. No predictor contains future/post-kickoff information.

No gate may be weakened after TEST is opened. If V1 fails, it remains failed; a V2 requires a new preregistration before another untouched holdout/prospective test.

## What PASS would and would not mean

PASS would authorize a **research probability model** for generic 1X2 and forward monitoring. It would not create a betting strategy, canonical rule or stake change by itself. Value/EV can only be evaluated prospectively at an executable price after the historical probability gate passes.

FAIL means the no-vig market baseline remains the honest generic 1X2 probability display. R1/R2/R3 remain untouched either way.

## Explicit prohibitions

- No odds bucket selection after TEST.
- No league removal/addition after TEST.
- No P1/P2-only rescue if the multiclass model fails.
- No changing calibration thresholds after seeing results.
- No using Stage71B TEST findings as fitted model features.
- No auto-promotion to canonical.
- No historical backfill into clean forward ledgers.
