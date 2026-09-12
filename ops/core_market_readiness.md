# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-12T06:36:07Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — COLLECTING_CLOSES
- Openers: 143 rows / 143 fixtures; snapshots: 634 rows / 121 fixtures; closes: 13 rows / 13 fixtures.
- Marathonbet close coverage: 92.31%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_13/120
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — COLLECTING_CLOSES
- Openers: 127 rows / 127 fixtures; snapshots: 463 rows / 107 fixtures; closes: 11 rows / 11 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_11/120
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — COLLECTING_CLOSES
- Openers: 740 rows / 143 fixtures; snapshots: 2768 rows / 121 fixtures; closes: 68 rows / 13 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_13/120
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — COLLECTING_CLOSES
- Openers: 1311 rows / 143 fixtures; snapshots: 7816 rows / 121 fixtures; closes: 120 rows / 13 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_13/120
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
