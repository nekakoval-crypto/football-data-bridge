# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-18T18:34:07Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 258 rows / 258 fixtures; snapshots: 2086 rows / 258 fixtures; closes: 139 rows / 139 fixtures.
- Marathonbet close coverage: 94.24%; settlement coverage: 99.28%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 234 rows / 234 fixtures; snapshots: 1793 rows / 234 fixtures; closes: 123 rows / 123 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.19%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1330 rows / 258 fixtures; snapshots: 10177 rows / 258 fixtures; closes: 726 rows / 139 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.28%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 2399 rows / 258 fixtures; snapshots: 21089 rows / 258 fixtures; closes: 1283 rows / 139 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.28%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
