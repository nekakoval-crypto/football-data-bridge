# PBK Core Market Data Readiness

Обновлено UTC: 2026-10-10T00:49:45Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 402 rows / 402 fixtures; snapshots: 3652 rows / 389 fixtures; closes: 277 rows / 277 fixtures.
- Marathonbet close coverage: 95.31%; settlement coverage: 99.64%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 367 rows / 367 fixtures; snapshots: 3204 rows / 355 fixtures; closes: 255 rows / 255 fixtures.
- Marathonbet close coverage: 99.61%; settlement coverage: 99.61%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 2063 rows / 402 fixtures; snapshots: 18039 rows / 389 fixtures; closes: 1428 rows / 277 fixtures.
- Marathonbet close coverage: 99.64%; settlement coverage: 99.64%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 3763 rows / 402 fixtures; snapshots: 35634 rows / 389 fixtures; closes: 2582 rows / 277 fixtures.
- Marathonbet close coverage: 99.64%; settlement coverage: 99.64%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
