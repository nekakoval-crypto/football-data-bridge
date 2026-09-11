# Stage71I — Core prospective market settlement policy

Locked before the first Stage71I run.

## Purpose
Convert frozen prospective market-close rows into outcome-labelled research observations for the four raw collection families: ИТБ/ИТМ, 1Х/Х2/12, European Handicap 3-way and Ф1(0)/Ф2(0). Stage71I is a research data layer only; it cannot create signals, WATCH events or strategy promotions.

## Source of match outcome
- API-Football final fixture result.
- Only status `FT` is auto-settled.
- Regulation-time full-time score is used.
- AET/PEN/AWD/WO/ABD/CANC and any ambiguous/non-final status are not auto-settled; they remain outside the settled dataset for manual/review handling.

## Settlement rules
### TEAM_TOTAL
For the captured team and line:
- ИТБ: WIN if team goals > line, LOSS if team goals < line, PUSH if equal.
- ИТМ: inverse of ИТБ, with PUSH on equality.

### DOUBLE_CHANCE
- 1Х: WIN on home win or draw; otherwise LOSS.
- Х2: WIN on away win or draw; otherwise LOSS.
- 12: WIN when match is not a draw; otherwise LOSS.

### DRAW_NO_BET / Ф(0)
- Ф1(0): WIN on home win, LOSS on away win, PUSH on draw.
- Ф2(0): inverse.

### EUROPEAN_HANDICAP
`home_handicap_line` is added to the home team's final score. The adjusted home score is compared with away goals:
- HOME selection wins if adjusted home > away.
- DRAW selection wins if equal.
- AWAY selection wins if adjusted home < away.
Exactly one of the three selections is WIN; the other two are LOSS.

## Price P/L
For every available Bet365 observed close and Marathonbet observed close:
- WIN P/L at flat 1u = odds - 1.
- LOSS P/L = -1.
- PUSH P/L = 0.
- Missing price => P/L blank.

These P/L values describe the frozen research close price only. They are not proof a real bet was placed.

## Data integrity
- Settlement is append-only by a deterministic `settlement_key`.
- A market row is settled only after its observed close exists and fixture status is FT.
- No historical backfill from matches before the prospective capture.
- `signals_created` must always remain 0.
- Discovery analysis may use these rows only under the Stage71H readiness/preregistration firewall.
