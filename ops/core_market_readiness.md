# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-17T06:39:23Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 256 rows / 256 fixtures; snapshots: 1466 rows / 204 fixtures; closes: 137 rows / 137 fixtures.
- Marathonbet close coverage: 94.16%; settlement coverage: 98.54%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 232 rows / 232 fixtures; snapshots: 1212 rows / 185 fixtures; closes: 121 rows / 121 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.17%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1295 rows / 256 fixtures; snapshots: 7062 rows / 204 fixtures; closes: 716 rows / 137 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 98.54%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 2373 rows / 256 fixtures; snapshots: 15351 rows / 204 fixtures; closes: 1266 rows / 137 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 98.54%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
