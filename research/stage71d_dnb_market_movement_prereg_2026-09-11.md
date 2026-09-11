# Stage71D — Ф(0) / Draw No Bet market-movement research

Date locked: 2026-09-11
Status: PREREGISTERED BEFORE TEST

## Market and source

This stage uses only real historical Bet365 Asian Handicap prices where the handicap line is exactly 0.0, which is economically the full-time Draw No Bet / Ф(0) market:
- Ф1(0): home side, draw = stake returned;
- Ф2(0): away side, draw = stake returned.

Canonical source: `Football_Top5_2016-2026.csv`.
Opening fields: `AHh`, `B365AHH`, `B365AHA`.
Closing fields: `AHCh`, `B365CAHH`, `B365CAHA`.

A match is eligible for this research only if both opening and closing handicap are exactly 0.0 and both Bet365 prices are complete at both timestamps. A line that moved to ±0.25 or another handicap is not silently converted back to DNB.

## Time split

- TRAIN: 2019/20–2022/23
- TEST: 2023/24–2025/26

The split is fixed before any TEST ROI is viewed.

## Locked hypotheses

Primary movement threshold: +0.03 no-vig probability points from Bet365 opening to Bet365 close.

For each Big-5 league, test exactly two directional hypotheses:

- D1 HOME DNB STEAM: no-vig P(Ф1(0)) increases by at least +0.03; historical execution = Bet365 closing Ф1(0) price.
- D2 AWAY DNB STEAM: no-vig P(Ф2(0)) increases by at least +0.03; historical execution = Bet365 closing Ф2(0) price.

No form, table, weekday, team-name, favorite-status, odds-band or other post-hoc filter is allowed in this stage.

## Settlement

Flat 1u.
- selected side wins match: profit = closing odds - 1;
- draw: profit = 0 (push / stake returned);
- selected side loses: profit = -1.

## Candidate gate

A league+direction candidate must satisfy all of the following:
- TRAIN ROI > 0;
- TEST ROI > 0;
- TEST sample >= 60 bets;
- at least 2 of the 3 TEST seasons positive when all three contain bets;
- nearby movement thresholds +0.02 / +0.03 / +0.04 have the same TEST ROI sign;
- observed chronological TEST MDD is reported;
- one-sided significance and BH/FDR across all league×direction tests are reported, but p-value is not the sole promotion criterion.

If the available exact-zero-line sample makes the preregistered n>=60 gate impossible, the stage may conclude `INSUFFICIENT_SAMPLE`; the threshold will not be lowered after seeing TEST performance.

## Promotion rule

Passing this historical screen creates at most a `FORWARD WATCH CANDIDATE`. It does not create R4/R5 and does not enter canonical forward automatically. Any candidate must receive a separate prospective definition and forward validation.

## Relationship to Double Chance

1Х / Х2 / 12 are not the same market as Ф(0). They are not reconstructed from 1X2 implied probabilities and called executable odds. If direct historical Double Chance prices are absent, that family will use a separate prospective capture stage.
