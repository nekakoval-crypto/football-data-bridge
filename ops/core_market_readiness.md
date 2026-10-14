# PBK Core Market Data Readiness

Обновлено UTC: 2026-10-14T17:22:42Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 503 rows / 503 fixtures; snapshots: 4208 rows / 407 fixtures; closes: 393 rows / 393 fixtures.
- Marathonbet close coverage: 94.91%; settlement coverage: 99.49%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 466 rows / 466 fixtures; snapshots: 3710 rows / 372 fixtures; closes: 359 rows / 359 fixtures.
- Marathonbet close coverage: 99.72%; settlement coverage: 99.44%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 2580 rows / 509 fixtures; snapshots: 20860 rows / 408 fixtures; closes: 2015 rows / 393 fixtures.
- Marathonbet close coverage: 99.75%; settlement coverage: 99.49%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 4737 rows / 505 fixtures; snapshots: 40819 rows / 407 fixtures; closes: 3669 rows / 393 fixtures.
- Marathonbet close coverage: 99.75%; settlement coverage: 99.49%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
