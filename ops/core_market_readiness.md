# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-18T00:38:06Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 257 rows / 257 fixtures; snapshots: 1729 rows / 254 fixtures; closes: 138 rows / 138 fixtures.
- Marathonbet close coverage: 94.2%; settlement coverage: 99.28%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 233 rows / 233 fixtures; snapshots: 1460 rows / 230 fixtures; closes: 122 rows / 122 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.18%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1320 rows / 257 fixtures; snapshots: 8382 rows / 254 fixtures; closes: 721 rows / 138 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.28%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 2388 rows / 257 fixtures; snapshots: 17785 rows / 254 fixtures; closes: 1274 rows / 138 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 99.28%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
