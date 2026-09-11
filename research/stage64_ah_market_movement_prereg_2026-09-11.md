# PBK Stage 64 — Asian Handicap Market Movement Preregistration

Date: 2026-09-11  
Status: **PREREGISTERED BEFORE TEST INSPECTION**

## Goal

Test whether Asian Handicap market movement contains a separate, reproducible signal. This is not a re-run of Stage8 AH baselines: Stage8 showed that blindly betting either AH side is not an edge.

## Data and split

- Canonical `Football_Top5_2016-2026.csv`
- Big-5 leagues: Premier League, La Liga, Serie A, Bundesliga, Ligue 1
- Require complete Bet365 first and close AH data:
  - first line `AHh`, prices `B365AHH/B365AHA`
  - close line `AHCh`, prices `B365CAHH/B365CAHA`
- TRAIN: 2019/20–2022/23
- TEST: 2023/24–2025/26
- Flat stake: 1u
- Historical execution: Bet365 closing AH line and closing price

## Asian-handicap settlement

Settlement follows standard AH quarter-line logic and reproduces the old Stage8 baseline results exactly.

Examples:
- Ф1(-0.25) = half stake Ф1(0) + half stake Ф1(-0.5)
- Ф1(-0.75) = half stake Ф1(-0.5) + half stake Ф1(-1.0)
- Push = 0u on that portion
- Half win / half loss are preserved; they are not rounded into full wins/losses.

`AHh/AHCh` are home-team handicap lines. Negative home line means home is the AH favorite; positive home line means away is the AH favorite.

## Primary rules

### AH1 — Favorite Line Steam

- Opening AH line is non-zero, so there is a defined AH favorite.
- The same favorite remains favored at close (line sign does not flip and close is non-zero).
- Closing line strengthens the opening favorite by at least **0.25 goals**:
  - home favorite: `AHh - AHCh >= 0.25`
  - away favorite: `AHCh - AHh >= 0.25`
- Bet the opening favorite at the **closing AH line** and Bet365 closing AH price.

User-facing selection examples: Ф1(-0.75), Ф2(-0.5), etc.

### AH2 — Favorite Price Steam, Same Line

- Opening AH line is non-zero.
- Closing AH line equals opening AH line exactly.
- Convert the two Bet365 AH prices into no-vig side probabilities.
- Opening favorite's no-vig probability increases by at least **+0.03** from first to close.
- Bet the opening favorite at the same closing AH line and Bet365 closing price.

## Candidate requirements

A league×rule is only a historical candidate if all apply:

1. TRAIN ROI > 0.
2. TEST ROI > 0.
3. At least 60 TEST bets.
4. At least 2 of 3 TEST seasons are individually positive.
5. Robustness keeps the TEST ROI sign:
   - AH1: stricter line move >=0.50 goals must remain positive when sample is non-trivial; no smaller non-zero threshold exists because AH lines move in 0.25 increments.
   - AH2: nearby probability thresholds 0.02 and 0.04 must keep the same TEST ROI sign.
6. Report average closing price and maximum drawdown.
7. No canonical rule is created from history alone; any passing candidate becomes forward WATCH first.

## Multiple testing

Exactly 10 primary tests: 5 leagues × 2 rules. Report one-sided mean-return p-values and Benjamini-Hochberg q-values across the 10 TEST results.

## Boundary

- R1/R2/R3 unchanged.
- Stage61/62/63 remain separate research watches.
- Stage64 is research only until a preregistered candidate passes and then survives prospective forward evidence.
