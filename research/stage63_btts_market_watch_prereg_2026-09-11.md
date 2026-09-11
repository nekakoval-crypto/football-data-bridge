# PBK Stage 63 — ОЗ Market Movement Prospective Watch

Date: 2026-09-11  
Status: **PREREGISTERED PROSPECTIVE DATA COLLECTION — NOT A BETTING RULE**

## Why there is no historical TRAIN→TEST backtest

The canonical `Football_Top5_2016-2026.csv` contains Bet365 first/close prices for 1X2 and O/U 2.5, but it does **not** contain historical Bet365 first/close prices for Both Teams To Score (BTTS / ОЗ — Да/Нет).

Therefore Stage 63 must not manufacture a historical edge from outcome data alone. Historical BTTS form filters from earlier stages are a different hypothesis and are not reused here.

## Prospective scope

- Big-5 domestic top divisions: Premier League, La Liga, Serie A, Bundesliga, Ligue 1.
- Market: Both Teams To Score.
- User display notation: **ОЗ — Да / ОЗ — Нет**.
- Reference bookmaker: Bet365.
- User executable bookmaker observed in parallel: Marathonbet.
- Flat observation threshold: absolute no-vig probability movement >= 3 percentage points from the frozen opener.
- This threshold is an observation trigger only, **not a betting threshold**.

## Data protocol

For every upcoming Big-5 fixture:

1. Freeze the first complete Bet365 ОЗ — Да / ОЗ — Нет pair observed by Stage63.
2. Convert the pair to no-vig P(ОЗ — Да) and P(ОЗ — Нет).
3. Append timestamped Bet365 and Marathonbet snapshots near kickoff.
4. Record the first +3 pp move toward **ОЗ — Да** as `YES_STEAM_WATCH`.
5. Record the first +3 pp move toward **ОЗ — Нет** as `NO_STEAM_WATCH`.
6. A crossing is a research WATCH only. It must not enter canonical `forward_log.csv`.
7. After kickoff, freeze the latest observed pre-kickoff snapshot as the observed close.
8. Preserve Marathonbet price at the first crossing and at observed close when available.

## Governance

- R1/R2/R3 remain unchanged.
- Stage61 and Stage62 remain separate research watches.
- Stage63 creates no R4/R5/R6 label.
- No historical ROI is claimed for Stage63.
- No row is backfilled before the first live capture date.
- Any future strategy decision must be based on the prospective sample accumulated after this preregistration and must explicitly account for sample size, execution availability and multiple testing.
