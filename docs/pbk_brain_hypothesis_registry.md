# PBK Brain — Hypothesis Registry v2

## Purpose

`config/pbk_hypothesis_registry.json` is the authoritative machine-readable inventory of PBK canonical strategies, research hypotheses, market families and decision-model work. An idea discussed in chat is not considered implemented merely because it was discussed: it must have a stable registry ID and an evidence status.

The registry is governance metadata only. It does **not** create a bet, change eligibility/exposure, authorize value/EV, promote WATCH/RESEARCH to canonical, or change the UI.

## Core rule

PBK keeps four different concepts separate:

`data exists` ≠ `metric works` ≠ `hypothesis passed` ≠ `value exists today`.

For that reason v2 removes `DATA_READY` from the hypothesis lifecycle. Data availability is recorded separately in `data_readiness` (`NOT_READY`, `PARTIAL`, `READY`, `LIVE_CAPTURE`).

## Required inventory columns

Every registry item explicitly carries the machine equivalent of:

`ID → idea → market → selection/side → league/scope → filters → required data → HIST → TRAIN → TEST → FORWARD → status`.

`evidence_stage` always contains four fields: `hist`, `train`, `test`, `forward`. Evidence may be `NOT_STARTED`, `NOT_RECORDED`, `COLLECTING`, a scope-qualified PASS, or another explicit non-empty state. Missing evidence must never be silently interpreted as PASS.

## Lifecycle v2

The only hypothesis statuses are:

`IDEA → SPEC_LOCKED → HIST_TESTED → PASSED → FORWARD → REVIEW → CANONICAL`

Administrative alternatives are `REJECTED` and `PAUSED`.

- `IDEA` — work item exists; data may already be available, but validation has not started.
- `SPEC_LOCKED` — rule/model specification was frozen before outcome evaluation.
- `HIST_TESTED` — historical evaluation ran; no PASS is implied.
- `PASSED` — required historical/OOS gate passed for the explicitly stated scope only.
- `FORWARD` — prospective immutable collection/evaluation is active.
- `REVIEW` — forward evidence reached its preregistered review point and awaits manual governance.
- `CANONICAL` — explicitly approved canonical betting authority.

No transition is automatic.

## Generic 1X2 v1

`GENERIC_1X2_PROBABILITY_V1` is registered as `FORWARD / RESEARCH`.

Its historical result is deliberately recorded as **pooled Big-5 only**. The historical pooled PASS does not prove Premier League, La Liga, Serie A, Bundesliga or Ligue 1 independently. Prospective validation is therefore official **per league**, across all 16 locked leagues. Pooled Big-5/all-16 views are diagnostic only.

The registry does not authorize Generic 1X2 for EV/value, stakes, production probability, R1/R2/R3 changes or automatic canonical promotion.

## Market coverage

The inventory explicitly includes separate work items for:

- home favourite P1, away favourite P2, draw X, outright underdogs, fading an overvalued favourite and large-price longshots;
- totals TB/TM;
- BTTS Yes/No;
- team totals ITB1/ITM1/ITB2/ITM2;
- executable half-line handicaps;
- DNB/F0;
- double chance 1X/X2/12;
- European handicap;
- Asian handicap with explicit settlement semantics.

Market capture/readiness is not strategy validation. A market can have `LIVE_CAPTURE` data while its hypothesis status remains `IDEA`.

## Player, team and matchup work

Player Overall, Player Form, Player Importance, XI Quality and Rotation remain separate research items. The old combined `ABSENCE_RETURN_IMPACT` item is retained as `PAUSED` for traceability and split into `ABSENCE_IMPACT` and `RETURN_IMPACT`.

`TEAM_GRADES` tracks the planned Attack, Defence, Form, Home, Away, Schedule/Fatigue, Squad, XI, Availability, Motivation/Objectives and Market components. These must not be blindly averaged into an Overall score before validation.

`MATCHUP_GRADE` separately tracks style interactions such as press vs weak build-up, set pieces, tempo vs fatigue, wing mismatch, low block, aerial play and transitions.

## Probability, value and scanner guardrails

`MARKET_SCANNER_ALL_SUPPORTED` records the requirement to inspect the supported market set for each match rather than stop after finding one familiar signal. It includes P1/X/P2, 1X/X2/12, handicaps, DNB, TB/TM, BTTS and both teams' totals where available.

`PROBABILITY_VALUE_ALL_MARKETS` requires a separate PBK probability for the actual bet/market being evaluated. A probability from one market or selection may never be transferred to another. Unsupported families return `NO_VALIDATED_MODEL` rather than a fabricated probability.

`HIGH_PROBABILITY_VS_VALUE` preserves the distinction that a short/high-probability price is not automatically safe or valuable. `LONGSHOT_UNDERDOG_ENGINE` preserves the opposite rule: large odds alone are never value.

## Historical/context policy

H2H, home/away profile, weekday/time, rest/schedule, cup/Europe load, season objectives, referee and weather are registered research/context layers. Context cannot mutate canonical eligibility by itself. H2H must preserve venue orientation, sample size, recency, season spread and the ordinary team baseline.

## Locked rules and UI freeze

R1/R2/R3 definitions remain hard-locked. The competition scope remains the locked 16 leagues. Historical results never enter the clean forward journal.

`ui_freeze=true` remains in force. Brain/data/validation work comes first; visual/UI work resumes only after the registry, scanner, grades/context and Decision Engine have enough real logic to justify presentation.
