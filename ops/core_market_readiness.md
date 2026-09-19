# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-19T12:36:04Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 264 rows / 264 fixtures; snapshots: 2422 rows / 264 fixtures; closes: 152 rows / 152 fixtures.
- Marathonbet close coverage: 94.08%; settlement coverage: 99.34%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 241 rows / 241 fixtures; snapshots: 2111 rows / 241 fixtures; closes: 135 rows / 135 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.26%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1359 rows / 264 fixtures; snapshots: 11859 rows / 264 fixtures; closes: 793 rows / 152 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.34%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 2458 rows / 264 fixtures; snapshots: 24154 rows / 264 fixtures; closes: 1409 rows / 152 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.34%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
