# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-19T00:37:42Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 259 rows / 259 fixtures; snapshots: 2198 rows / 259 fixtures; closes: 147 rows / 147 fixtures.
- Marathonbet close coverage: 93.88%; settlement coverage: 99.32%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 237 rows / 237 fixtures; snapshots: 1900 rows / 237 fixtures; closes: 130 rows / 130 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.23%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1331 rows / 259 fixtures; snapshots: 10736 rows / 259 fixtures; closes: 768 rows / 147 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.32%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 2400 rows / 258 fixtures; snapshots: 22113 rows / 258 fixtures; closes: 1363 rows / 147 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.32%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
