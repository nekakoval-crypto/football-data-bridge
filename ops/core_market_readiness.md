# PBK Core Market Data Readiness

Обновлено UTC: 2026-10-10T18:40:55Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 410 rows / 410 fixtures; snapshots: 3986 rows / 393 fixtures; closes: 285 rows / 285 fixtures.
- Marathonbet close coverage: 95.09%; settlement coverage: 99.3%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 374 rows / 374 fixtures; snapshots: 3502 rows / 358 fixtures; closes: 262 rows / 262 fixtures.
- Marathonbet close coverage: 99.62%; settlement coverage: 99.24%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 2105 rows / 410 fixtures; snapshots: 19721 rows / 393 fixtures; closes: 1468 rows / 285 fixtures.
- Marathonbet close coverage: 99.65%; settlement coverage: 99.3%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 3842 rows / 410 fixtures; snapshots: 38751 rows / 393 fixtures; closes: 2653 rows / 285 fixtures.
- Marathonbet close coverage: 99.65%; settlement coverage: 99.3%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
