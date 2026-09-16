# PBK Generic 1X2 Probability v1 — per-league forward review protocol

Date: 2026-09-16  
Authority: RESEARCH  
Historical result: `PASS_HISTORICAL_PROBABILITY_GATE`  
Forward phase: `FORWARD_REVIEW_REQUIRED`

## Purpose

Generic 1X2 Probability v1 passed its preregistered historical out-of-sample probability gate on the pooled Big-5 historical dataset. That result is valid as a pooled Big-5 result only. It does **not** prove that the model works independently in Premier League, La Liga, Serie A, Bundesliga or Ligue 1, and it says nothing about the 11 extended leagues that were absent from that historical TEST.

Forward validation is therefore performed **separately for each of the 16 locked PBK leagues**.

There is no official pooled Big-5 forward verdict and no combined 16-league verdict.

## Frozen model

The probability transform is unchanged:

- M0: Bet365 1X2 no-vig probabilities.
- M1: `softmax(log(p_market_c) + alpha_c)`.
- `alpha_H = -0.018000000000000002`
- `alpha_D = 0.0`
- `alpha_A = -0.004`

No fitting, tuning, league-specific alpha adjustment, odds-band adjustment, subgroup rescue or parameter update is allowed inside Generic 1X2 v1.

If a league requires a changed model, that must be a separately named/versioned research model.

## Locked 16-league forward universe

Every league below receives an independent forward ledger view and an independent validation status.

Historical pooled Big-5 members:

- Premier League
- La Liga
- Serie A
- Bundesliga
- Ligue 1

These leagues carry the annotation:

`POOLED_BIG5_HISTORICAL_PASS_ONLY_NOT_LEAGUE_SPECIFIC`

That annotation is context only; none of these five starts with an individual league PASS.

Historically unvalidated extended leagues:

- Austrian Bundesliga
- Belgian Pro League
- Danish Superliga
- A Lyga
- Virsliga
- Eredivisie
- Eliteserien
- Ekstraklasa
- Primeira Liga
- Super Lig
- Scottish Premiership

These leagues carry:

`NO_HISTORICAL_VALIDATION`

All 16 begin league-specific forward monitoring from prospective observations.

## Market and snapshot rule

Market:

`Bet365 Match Winner 1X2`

A fixture is accepted only when a complete valid Bet365 H/D/A vector is observed before kickoff.

There is:

- no bookmaker substitution;
- no Avg fallback;
- no historical backfill;
- no retroactive reconstruction of a missed prematch observation.

For each fixture freeze the:

`FIRST_COMPLETE_VALID_BET365_PREMATCH_OBSERVATION`

Both the source observation time and monitor processing time must be strictly before kickoff.

Once frozen, later prices cannot overwrite the record.

## Settlement

Settlement is stored separately and append-only.

A settlement is accepted only when:

- a frozen prematch event exists;
- result is H, D or A;
- settlement time is after kickoff.

Settlement computes only probability-quality metrics:

- multiclass Brier for M0 and M1;
- multiclass log-loss for M0 and M1;
- M1 H/D/A calibration.

ROI, profit, EV, value labels and stake outcomes remain outside this protocol.

## Independent league review

The formal review unit is:

`LEAGUE`

Each league has its own:

- frozen prematch count;
- settled count;
- H/D/A outcome counts;
- M0 and M1 multiclass Brier;
- M0 and M1 log-loss;
- H/D/A M1 calibration;
- probability-sum guard;
- forward-only/no-backfill guard;
- sample readiness;
- status.

The currently frozen minimum sample is applied **per league**:

- at least 1,000 settled fixtures in that league;
- at least 150 H outcomes in that league;
- at least 150 D outcomes in that league;
- at least 150 A outcomes in that league.

Diagnostic checkpoints of 250 and 500 settled fixtures are also per league.

For a league-specific forward PASS all of the following must hold for that league only:

1. M1 multiclass Brier is strictly lower than M0.
2. M1 log-loss is strictly lower than M0.
3. M1 absolute calibration error is at most 0.03 for H, D and A.
4. Every M1 vector sums to one within `1e-9`.
5. All accepted observations pass forward-only/no-backfill guards.

League statuses:

- `COLLECTING`
- `FORWARD_REVIEW_READY_PASS`
- `FORWARD_REVIEW_READY_FAIL`

One league may PASS while another FAILS or remains COLLECTING.

A result from one league must never rescue, weaken, strengthen or otherwise determine another league's verdict.

## Pooled diagnostics

Two pooled views may be reported for diagnostics:

- pooled Big-5;
- pooled all 16 leagues.

Both must always have status:

`DIAGNOSTIC_ONLY`

They are descriptive summaries, not official forward verdicts.

The historical pooled Big-5 PASS remains preserved as historical evidence about the pooled dataset only.

## Governance locks

- `review_unit = LEAGUE`
- `pooled_big5_diagnostic_only = true`
- `combined_16_league_verdict = false`
- `authority = RESEARCH`
- `creates_signal = false`
- `value_authorized = false`
- `stake_changes_authorized = false`
- `profitability_or_roi_conclusion = false`
- `r1_r2_r3_changes_authorized = false`
- `production_integration_authorized = false`
- `ui_integration_authorized = false`
- `automatic_canonical_promotion = false`
- `manual_governance_review_required = true`

A league-specific forward PASS authorizes only a later governance review for that league. It does not automatically make the model CANONICAL or authorize betting/value/stakes.

## Implementation boundary

The forward core captures and settles all 16 leagues but does not itself poll a provider. A separate integration may feed genuinely prospective Bet365 observations into the core.

The historical canonical CSV is not an input to this forward monitor and must not be used to seed the forward journals.
