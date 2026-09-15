# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-15T06:40:11Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 211 rows / 211 fixtures; snapshots: 1225 rows / 137 fixtures; closes: 121 rows / 121 fixtures.
- Marathonbet close coverage: 95.87%; settlement coverage: 100.0%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — COLLECTING_CLOSES
- Openers: 194 rows / 194 fixtures; snapshots: 989 rows / 121 fixtures; closes: 107 rows / 107 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_107/120
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1053 rows / 208 fixtures; snapshots: 5859 rows / 137 fixtures; closes: 634 rows / 121 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 1920 rows / 207 fixtures; snapshots: 13199 rows / 137 fixtures; closes: 1115 rows / 121 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
