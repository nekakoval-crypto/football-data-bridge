# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-25T00:39:48Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 267 rows / 267 fixtures; snapshots: 2763 rows / 267 fixtures; closes: 267 rows / 267 fixtures.
- Marathonbet close coverage: 95.13%; settlement coverage: 99.63%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 246 rows / 246 fixtures; snapshots: 2424 rows / 246 fixtures; closes: 246 rows / 246 fixtures.
- Marathonbet close coverage: 99.59%; settlement coverage: 99.59%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1378 rows / 267 fixtures; snapshots: 13574 rows / 267 fixtures; closes: 1377 rows / 267 fixtures.
- Marathonbet close coverage: 99.63%; settlement coverage: 99.63%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 2488 rows / 267 fixtures; snapshots: 27273 rows / 267 fixtures; closes: 2483 rows / 267 fixtures.
- Marathonbet close coverage: 99.63%; settlement coverage: 99.63%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
