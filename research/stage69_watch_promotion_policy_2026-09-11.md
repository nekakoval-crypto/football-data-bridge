# PBK Stage 69 — WATCH Promotion Gate

Date: 2026-09-11  
Status: **LOCKED BEFORE ANY PROSPECTIVE WATCH SETTLEMENTS**

## Purpose

Prevent a research WATCH from becoming a canonical R-rule just because a small live sample looks attractive.

Stage69 never creates an R-rule automatically. It only says whether a WATCH family has collected enough prospective evidence to deserve a separate manual review.

## Scope

### Stage61 — АПЛ favorite steam
Historical support exists from the preregistered Stage61 TRAIN→TEST study, but the live action point is the **first observed crossing**, not the historical close. Therefore prospective crossing performance must be validated independently.

### Stage62 — Бундеслига ТБ(2.5) steam
Historical support exists from the preregistered Stage62 TRAIN→TEST study, but the live action point is again the **first observed crossing**. Prospective crossing performance must be validated independently.

### Stage63 — Big-5 ОЗ market movement
There is **no historical first/close BTTS dataset** in the canonical project. Stage63 is discovery-only. It is not allowed to move directly from its current WATCH data into an R-rule, regardless of ROI. Any promising league×direction finding must first become a separately preregistered hypothesis and then start a fresh holdout window.

## Review gate for Stage61 / Stage62

A family becomes `REVIEW_ELIGIBLE` only when all conditions below are true:

1. At least **60 settled prospective first-crossing rows with an executable Marathonbet price**.
2. Marathonbet price coverage at crossing is at least **90%** across all recorded crossings.
3. Overall prospective first-crossing ROI is **strictly positive**.
4. Chronological first half of executable settled rows has ROI **> 0**.
5. Chronological second half of executable settled rows has ROI **> 0**.
6. At least **90%** of settled rows have an observed pre-kickoff close classification.
7. If at least 20 close-qualified settled rows exist, their ROI must be **>= 0**. If fewer than 20 exist, the family remains `COLLECTING_CLOSE_SUBSET` even if other conditions pass.

These thresholds are not tuned after results arrive.

## What REVIEW_ELIGIBLE means

It does **not** mean “promote to R4/R5”. It means the candidate has earned a separate locked review covering:
- prospective ROI and P/L at Marathonbet;
- chronological stability;
- closing persistence/reversion;
- observed drawdown;
- overlap/correlation with existing R1/R2/R3;
- whether the executable live definition is genuinely the same economic idea as the historical candidate.

Only after that separate review may a new canonical rule be proposed.

## Stage63 discovery boundary

Stage63 rows may be summarized by league and direction (`ОЗ — Да` / `ОЗ — Нет`), but current data is discovery data. A candidate discovered inside this sample must be frozen in a new preregistration and evaluated only on **future rows recorded after that freeze**. No direct promotion from the discovery sample is allowed.

## General prohibitions

- No alternative-market substitution after the fact.
- No changing the +3 pp threshold because another threshold looks better live.
- No historical backfill into prospective counts.
- No pooling unrelated leagues/directions merely to improve sample size.
- No automatic R-rule creation.
