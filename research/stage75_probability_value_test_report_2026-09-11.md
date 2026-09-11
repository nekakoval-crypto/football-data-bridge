# Stage75 — Probability & Value Engine — locked TEST report

Date: 2026-09-11
Policy/preregistration: `research/stage75_probability_value_policy_2026-09-11.md`
Status: HISTORICAL_TEST_OPENED_AFTER_POLICY_LOCK

## Result
All three currently locked canonical rule families pass the pre-registered v1 probability-calibration gate.

The candidate model is deliberately only a one-parameter rule-specific logit shift:
`p_pbk = logistic(logit(p_market) + alpha_rule)`.

### R1 — Serie A away favourite
- TRAIN N: 527
- TEST N: 321
- fitted alpha: +0.305647
- TEST observed hit rate: 62.9283%
- TEST mean no-vig market probability: 55.9087%
- TEST mean PBK calibrated probability: 63.1254%
- M0 Brier: 0.228516
- M1 Brier: 0.223993
- relative Brier improvement: 1.9795%
- M0 log-loss: 0.648757
- M1 log-loss: 0.638433
- relative log-loss improvement: 1.5914%
- calibration-in-the-large absolute error: 0.1970 percentage points
- Gate: PASS

### R2 — locked R1 + last-5 PPG condition
- TRAIN N: 397
- TEST N: 236
- fitted alpha: +0.310435
- TEST observed hit rate: 65.2542%
- TEST mean no-vig market probability: 56.3371%
- TEST mean PBK calibrated probability: 63.6318%
- M0 Brier: 0.223700
- M1 Brier: 0.216491
- relative Brier improvement: 3.2226%
- M0 log-loss: 0.638837
- M1 log-loss: 0.622590
- relative log-loss improvement: 2.5433%
- calibration-in-the-large absolute error: 1.6225 percentage points
- Gate: PASS

### R3 — Big-5 Monday/end-season draw
- TRAIN N: 64 (modern 2019/20–2021/22)
- TEST N: 91
- fitted alpha: +0.527591
- TEST observed hit rate: 36.2637%
- TEST mean no-vig market probability: 25.6117%
- TEST mean PBK calibrated probability: 36.6927%
- M0 Brier: 0.237790
- M1 Brier: 0.225793
- relative Brier improvement: 5.0450%
- M0 log-loss: 0.669977
- M1 log-loss: 0.642062
- relative log-loss improvement: 4.1665%
- calibration-in-the-large absolute error: 0.4290 percentage points
- Gate: PASS

## Gate audit
Pre-registered conditions:
1. TEST N >= 80: PASS for R1/R2/R3.
2. M1 Brier strictly below M0: PASS for all three.
3. M1 log-loss not worse than M0: PASS for all three.
4. abs(mean predicted - observed hit rate) <= 5pp: PASS for all three.
5. only decision-time historical predictor used: PASS.

## Interpretation
- `p_market` remains visible and is labelled market no-vig probability.
- `p_pbk` may now be labelled **PBK probability — historically validated / forward monitoring** for R1/R2/R3 only.
- Historical TEST validation does not make the estimate certainty and does not authorize new strategies.
- It is a calibration layer on top of already-valid rule eligibility, not a signal generator.
- It must now be frozen prospectively before kickoff and reviewed after >=50 settled forward predictions per rule.

## Ranking policy
For unique canonical exposures only:
- **Максимальная вероятность прохода** = highest frozen validated `p_pbk`.
- **Лучший value** = highest `EV = p_pbk * executable_user_odds - 1`.
- R1+R2 overlap remains one logical exposure; use validated R2 probability when R2 applies, otherwise R1.
- R3 conflicts remain manual review.
- WATCH/challenger/discovery remain excluded from recommendation ranking v1.

No stake sizing changes are authorized by this report.
