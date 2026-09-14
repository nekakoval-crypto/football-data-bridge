# PBK Core Market Data Readiness

Обновлено UTC: 2026-09-14T18:37:10Z

> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.

## Исход матча — П1 / Х / П2 — ACTIVE_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Continue clean forward and challenger governance

## Двойной шанс — 1Х / Х2 / 12 — COLLECTING_CLOSES
- Openers: 191 rows / 191 fixtures; snapshots: 1190 rows / 134 fixtures; closes: 108 rows / 108 fixtures.
- Marathonbet close coverage: 96.3%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_108/120
- Next gate: Freeze discovery sample, preregister hypothesis, test on independent future holdout

## Фора 0 — Ф1(0) / Ф2(0) — COLLECTING_CLOSES
- Openers: 171 rows / 171 fixtures; snapshots: 958 rows / 118 fixtures; closes: 95 rows / 95 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_95/120
- Next gate: Collect a new prospective discovery sample; any future hypothesis requires new preregistration and independent future holdout

## Азиатская фора — HISTORICAL_NO_CANDIDATE
- Blocking: NEW_INDEPENDENT_HYPOTHESIS_REQUIRED
- Next gate: Only a new independently preregistered hypothesis or regime-change prospective path

## Европейская фора 3-way — COLLECTING_CLOSES
- Openers: 989 rows / 191 fixtures; snapshots: 5689 rows / 134 fixtures; closes: 562 rows / 108 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_108/120
- Next gate: Freeze discovery sample, preregister line/selection logic, test on independent future holdout

## Тотал матча — ТБ / ТМ — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective WATCH promotion policy only; no automatic R-rule

## Индивидуальные тоталы — ИТБ/ИТМ — COLLECTING_CLOSES
- Openers: 1773 rows / 191 fixtures; snapshots: 12876 rows / 134 fixtures; closes: 998 rows / 108 fixtures.
- Marathonbet close coverage: 100.0%; settlement coverage: 100.0%.
- Blocking: CLOSED_FIXTURES_108/120
- Next gate: Freeze discovery sample, preregister team/line/selection logic, independent future holdout

## Обе забьют — ОЗ Да / Нет — WATCH_GOVERNED
- Blocking: нет на уровне data-readiness policy.
- Next gate: Prospective evidence and Stage69 promotion gate; no direct promotion from discovery sample
