# PBK Core Market Data Readiness

Обновлено UTC: 2026-10-11T00:48:44Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 438 rows / 438 fixtures; snapshots: 4049 rows / 393 fixtures; closes: 330 rows / 330 fixtures.
- Marathonbet close coverage: 94.55%; settlement coverage: 99.09%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 400 rows / 400 fixtures; snapshots: 3560 rows / 358 fixtures; closes: 301 rows / 301 fixtures.
- Marathonbet close coverage: 99.67%; settlement coverage: 99.0%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 2246 rows / 438 fixtures; snapshots: 20046 rows / 393 fixtures; closes: 1693 rows / 330 fixtures.
- Marathonbet close coverage: 99.7%; settlement coverage: 99.09%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 4115 rows / 438 fixtures; snapshots: 39339 rows / 393 fixtures; closes: 3086 rows / 330 fixtures.
- Marathonbet close coverage: 99.7%; settlement coverage: 99.09%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
