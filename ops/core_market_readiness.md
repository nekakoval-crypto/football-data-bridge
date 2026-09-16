# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-16T00:38:27Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — DISCOVERY_POOL_READY
- Openers: 228 rows / 228 fixtures; snapshots: 1275 rows / 145 fixtures; closes: 127 rows / 127 fixtures.
- Marathonbet close coverage: 94.49%; settlement coverage: 100.0%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — COLLECTING_CLOSES
- Openers: 208 rows / 208 fixtures; snapshots: 1033 rows / 128 fixtures; closes: 112 rows / 112 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_112/120
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — DISCOVERY_POOL_READY
- Openers: 1146 rows / 227 fixtures; snapshots: 6106 rows / 145 fixtures; closes: 665 rows / 127 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — DISCOVERY_POOL_READY
- Openers: 2061 rows / 223 fixtures; snapshots: 13646 rows / 143 fixtures; closes: 1170 rows / 127 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: нет на уровне data-readiness policy.
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
