# PBK Core Market Data Readiness

Обновлено UTC: 2026-10-12T06:12:18Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 463 rows / 463 fixtures; snapshots: 4156 rows / 393 fixtures; closes: 382 rows / 382 fixtures.
- Marathonbet close coverage: 94.76%; settlement coverage: 99.48%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 425 rows / 425 fixtures; snapshots: 3660 rows / 359 fixtures; closes: 348 rows / 348 fixtures.
- Marathonbet close coverage: 99.71%; settlement coverage: 99.43%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 2377 rows / 464 fixtures; snapshots: 20593 rows / 393 fixtures; closes: 1958 rows / 382 fixtures.
- Marathonbet close coverage: 99.74%; settlement coverage: 99.48%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 4350 rows / 463 fixtures; snapshots: 40330 rows / 393 fixtures; closes: 3567 rows / 382 fixtures.
- Marathonbet close coverage: 99.74%; settlement coverage: 99.48%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
