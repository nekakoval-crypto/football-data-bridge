# PBK Generic 1X2 Probability v1 — frozen OOS TEST result

Date: 2026-09-16  
Authority: RESEARCH  
Final verdict: `PASS_HISTORICAL_PROBABILITY_GATE`  
Research status: `HISTORICALLY_VALIDATED_RESEARCH`  
Next phase: `FORWARD_REVIEW_REQUIRED`

## Frozen research contract

Generic 1X2 Probability v1 was preregistered in PR #59 before TEST outcomes were opened. The locked design used Big-5 Bet365 complete 1X2 prices, TRAIN seasons 2019/20–2022/23, and TEST seasons 2023/24–2025/26. M0 is the Bet365 no-vig probability vector. M1 is the frozen multiclass intercept-shift calibration model with `alpha_D = 0` and `alpha_H` / `alpha_A` fitted on TRAIN only.

PR #60 added the fail-closed pre-TEST gate. It passed with `TEST_ALLOWED` before TEST outcomes were opened.

Before opening TEST, PR #61 corrected one execution/schema mismatch: the canonical snapshot uses lowercase `season`, while the original preregistered evaluator/config referenced `Season`. The correction changed only that schema lookup and did not change model design, split, optimizer, features, thresholds, classes, league scope, or acceptance criteria.

The exact frozen execution baseline used for the blind TEST was:

`aef23cf32284cbfda1a1e93be7391777d6b9d918`

Canonical source:

`Football_Top5_2016-2026.csv`

SHA-256:

`a49cd84b1b4d6d2aad2856d7c81b4ae8b34954dabf4dd356fe41588f370cd004`

## Recovery audit

The original one-time blind TEST opened TEST outcomes and reached metric computation, but its wrapper failed while persisting the output before the metrics were displayed or preserved. No model, configuration, split, threshold, optimizer, feature set, or acceptance criterion was changed after that opening.

Several recovery attempts stopped before the evaluator read the canonical TEST data: first because no usable Python interpreter was available in the isolated environment, and later because the Work sandbox blocked process execution before the CSV was opened. Those failed attempts did not reread TEST.

A governance-authorized deterministic recovery replay was then executed locally in Windows PowerShell using Python 3.12.10, the exact frozen commit above, and a source file whose SHA-256 matched the canonical snapshot exactly. The evaluator exited successfully and its raw stdout was preserved externally. No post-hoc tuning or alternate model was run.

This report records that already-completed frozen result. Creating this report does not rerun TEST and does not reread the canonical CSV.

## Frozen result

TRAIN usable rows: **7,198**  
TEST eligible rows: **5,256**

TEST outcomes:

- H: 2,262
- D: 1,346
- A: 1,648

TRAIN-only fitted parameters:

- `alpha_H = -0.018000000000000002`
- `alpha_D = 0.0`
- `alpha_A = -0.004`
- TRAIN log-loss: `0.9786826002938076`

### Proper scoring rules on locked TEST

| Metric | M0 Bet365 no-vig | M1 Generic 1X2 v1 | Improvement M0 - M1 | Relative improvement |
| --- | ---: | ---: | ---: | ---: |
| Multiclass Brier | 0.5743448663957984 | 0.5742689609113001 | 0.00007590548449831758 | 0.013216011657708247% |
| Log-loss | 0.9661933045794492 | 0.9660505956293809 | 0.0001427089500682932 | 0.014770227592335625% |

### M1 class calibration

| Class | Mean predicted | Observed rate | Absolute error | Outcomes |
| --- | ---: | ---: | ---: | ---: |
| H | 0.43673198135133834 | 0.430365296803653 | 0.006366684547685353 | 2,262 |
| D | 0.24979857634558597 | 0.2560882800608828 | 0.006289703715296829 | 1,346 |
| A | 0.3134694423030757 | 0.3135464231354642 | 0.00007698083238849573 | 1,648 |

## Frozen acceptance checks

All preregistered historical probability-gate conditions passed:

- TEST sample minimum: PASS
- H/D/A minimum class support: PASS
- M1 Brier strictly lower than M0: PASS
- M1 log-loss strictly lower than M0: PASS
- H/D/A absolute calibration error <= 0.03: PASS
- Probability vectors sum to one within the frozen tolerance: PASS
- No future/post-kickoff predictor: PASS

The preregistered M1 model strictly improved both Brier score and log-loss over the Bet365 no-vig baseline on the locked TEST set, satisfying the historical probability gate. The magnitude of improvement was small, so this result should be treated as successful historical validation of the probability calibration layer, not evidence of betting profitability or material economic edge.

## Governance consequence

Generic 1X2 Probability v1 advances from `SPEC LOCKED` to `HIST TESTED / PASSED` for research governance, with next phase `FORWARD_REVIEW_REQUIRED`.

This PASS does **not** authorize:

- CANONICAL status;
- betting strategy or stake changes;
- EV/value, Strong Value, Watch, or Longshot labels;
- R1/R2/R3 replacement or modification;
- production probability integration;
- UI integration.

`canonical_rules_changed = false`  
`value_authorized = false`  
`stake_changes_authorized = false`

No profitability or ROI conclusion is made by this historical probability test.
