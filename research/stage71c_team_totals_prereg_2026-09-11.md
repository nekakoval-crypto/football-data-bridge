# Stage71C — Individual Team Totals prospective market capture

Date locked: 2026-09-11
Status: PREREGISTERED / PROSPECTIVE DATA COLLECTION ONLY

## Why this stage exists

PBK must treat individual team totals as an independent market family, not as a substitute for match totals or BTTS. Examples include ИТБ1(1.5), ИТМ1(1.5), ИТБ2(1.5), ИТМ2(1.5), but there is no global restriction to the 1.5 line.

The canonical `Football_Top5_2016-2026.csv` does not contain bookmaker prices for individual team totals. Therefore Stage71C does **not** claim a historical backtest or a historical edge. Any apparent result reconstructed only from final goals without executable market odds would be rejected as a market backtest.

## Locked scope

Competitions: all 16 PBK national leagues already locked in Stage71.

Markets:
- home-team full-time goal total: ИТБ1(line) / ИТМ1(line)
- away-team full-time goal total: ИТБ2(line) / ИТМ2(line)

Time settlement: full-time regulation only unless a later strategy explicitly preregisters another convention.

Bookmakers:
- Bet365 = market reference / opener / observed close
- Marathonbet = executable user-price source when present

No global odds cap and no global team-total line cap.

## Data-collection protocol

For every upcoming fixture in the locked 16-league universe:
1. Discover the pre-match API-Football bet IDs for home-team and away-team goal totals from `/odds/bets`; do not hard-code an unverified ID.
2. Freeze the first complete Bet365 Over/Under pair observed for each team-side + line.
3. Preserve every available full-time line exposed by the provider rather than cherry-picking one line after seeing results.
4. Within the tracking horizon append timestamped Bet365 and Marathonbet price pairs.
5. After kickoff freeze the latest observed pre-kickoff pair for the same team-side + line as the observed close.
6. Never replace a missing price on one line with a neighbouring line after kickoff.

## Research governance

Stage71C produces market-history data, **not betting signals**.

There is no Stage71C WATCH crossing and no R4/R5 promotion from the raw capture layer.

Once enough settled fixtures exist, a separate analysis stage may use an initial discovery sample to define a candidate hypothesis. That hypothesis must freeze before its future test:
- league or league family;
- team side (home/away or symmetric rule);
- line or line-family;
- Over/Under direction;
- eligibility features;
- price convention;
- stake and settlement;
- minimum sample and promotion criteria.

The discovery sample used to choose that candidate may not be reused as the independent holdout. Promotion requires a new prospective holdout.

## Multiple-testing guard

Capturing many lines is permitted because capture is not hypothesis testing. Searching many captured lines and then declaring the best historical-looking line a strategy is prohibited. Any later candidate must pass a frozen-discovery → preregistration → new-holdout sequence.

## Relationship to other PBK markets

ИТБ/ИТМ is independent from:
- ТБ/ТМ матча;
- ОЗ — Да/Нет;
- 1X2;
- handicaps.

A match meeting a ТБ(2.5) WATCH condition does not automatically authorize an ИТБ selection, and vice versa.

## Deferred exotic universe

Correct score, combo markets (including ОЗ+ТБ/ТМ), bet-builder, player props, corners, cards, shots, offsides and time-band markets remain explicit PBK roadmap items under `DEFERRED_REQUIRED_LATER`; they are not permanently excluded.
