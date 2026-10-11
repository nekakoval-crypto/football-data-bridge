# PBK Core Market Data Readiness

Обновлено UTC: 2026-10-11T22:09:14Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 454 rows / 454 fixtures; snapshots: 4145 rows / 393 fixtures; closes: 356 rows / 356 fixtures.
- Marathonbet close coverage: 94.66%; settlement coverage: 99.44%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — DISCOVERY_POOL_READY
- Openers: 416 rows / 416 fixtures; snapshots: 3649 rows / 359 fixtures; closes: 325 rows / 325 fixtures.
- Marathonbet close coverage: 99.69%; settlement coverage: 99.38%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 2327 rows / 454 fixtures; snapshots: 20537 rows / 393 fixtures; closes: 1826 rows / 356 fixtures.
- Marathonbet close coverage: 99.72%; settlement coverage: 99.44%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 4267 rows / 454 fixtures; snapshots: 40229 rows / 393 fixtures; closes: 3323 rows / 356 fixtures.
- Marathonbet close coverage: 99.72%; settlement coverage: 99.44%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
