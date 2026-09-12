# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-12T00:37:54Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — COLLECTING_CLOSES
- Openers: 140 rows / 140 fixtures; snapshots: 527 rows / 116 fixtures; closes: 9 rows / 9 fixtures.
- Marathonbet close coverage: 88.89%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_9/120; MARATHONBET_CLOSE_COVERAGE_88.9%/90%
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — COLLECTING_CLOSES
- Openers: 124 rows / 124 fixtures; snapshots: 368 rows / 102 fixtures; closes: 7 rows / 7 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_7/120
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — COLLECTING_CLOSES
- Openers: 724 rows / 140 fixtures; snapshots: 2212 rows / 116 fixtures; closes: 47 rows / 9 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_9/120
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — COLLECTING_CLOSES
- Openers: 1283 rows / 140 fixtures; snapshots: 6843 rows / 116 fixtures; closes: 86 rows / 9 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_9/120
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
