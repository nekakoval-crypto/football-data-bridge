# PBK Core Market Data Readiness

Обновлено UTC: 2026-10-13T00:51:55Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 474 rows / 474 fixtures; snapshots: 4177 rows / 393 fixtures; closes: 383 rows / 383 fixtures.
- Marathonbet close coverage: 94.78%; settlement coverage: 99.48%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 436 rows / 436 fixtures; snapshots: 3681 rows / 359 fixtures; closes: 349 rows / 349 fixtures.
- Marathonbet close coverage: 99.71%; settlement coverage: 99.43%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 2408 rows / 473 fixtures; snapshots: 20701 rows / 393 fixtures; closes: 1964 rows / 383 fixtures.
- Marathonbet close coverage: 99.74%; settlement coverage: 99.48%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 4404 rows / 469 fixtures; snapshots: 40523 rows / 393 fixtures; closes: 3577 rows / 383 fixtures.
- Marathonbet close coverage: 99.74%; settlement coverage: 99.48%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
