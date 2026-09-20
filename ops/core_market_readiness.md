# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-20T12:36:19Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 267 rows / 267 fixtures; snapshots: 2715 rows / 267 fixtures; closes: 208 rows / 208 fixtures.
- Marathonbet close coverage: 94.71%; settlement coverage: 99.52%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 245 rows / 245 fixtures; snapshots: 2379 rows / 245 fixtures; closes: 189 rows / 189 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.47%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1377 rows / 267 fixtures; snapshots: 13330 rows / 267 fixtures; closes: 1076 rows / 208 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.52%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 2487 rows / 267 fixtures; snapshots: 26831 rows / 267 fixtures; closes: 1931 rows / 208 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.52%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
