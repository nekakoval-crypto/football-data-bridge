# PBK Stage 64 — Asian Handicap Market Movement Results

Date: 2026-09-11  
Status: **COMPLETE — NO FORWARD WATCH CANDIDATE**

Preregistration: `research/stage64_ah_market_movement_prereg_2026-09-11.md`

## Validation of settlement

The AH settlement implementation reproduces the original Stage8 baseline exactly. Example, Premier League TRAIN-modern 2019/20–2022/23:

- home AH baseline: 1,520 bets, ROI **−3.2349%**
- away AH baseline: 1,520 bets, ROI **−1.3615%**

This confirms quarter-lines, pushes and half-win/half-loss handling match the prior project logic.

## Primary results

| League | Rule | TRAIN n | TRAIN ROI | TEST n | TEST ROI | TEST P/L u | + TEST seasons | Avg close | TEST MDD | one-sided p | BH q | Pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Premier League | AH1 Favorite Line Steam | 234 | -10.00% | 176 | -5.23% | -9.21 | 1/3 | 2.004 | 14.32u | 0.771 | 0.962 | NO |
| Premier League | AH2 Favorite Price Steam, same line | 101 | -8.55% | 66 | +4.76% | +3.14 | 2/3 | 1.857 | 4.67u | 0.325 | 0.962 | **NO — TRAIN** |
| La Liga | AH1 Favorite Line Steam | 268 | -11.05% | 151 | -10.85% | -16.39 | 1/3 | 1.996 | 21.05u | 0.926 | 0.962 | NO |
| La Liga | AH2 Favorite Price Steam, same line | 117 | -15.65% | 92 | -2.64% | -2.43 | 2/3 | 1.866 | 8.19u | 0.615 | 0.962 | NO |
| Serie A | AH1 Favorite Line Steam | 285 | -6.45% | 137 | -2.55% | -3.50 | 2/3 | 2.004 | 13.76u | 0.627 | 0.962 | NO |
| Serie A | AH2 Favorite Price Steam, same line | 122 | +5.91% | 79 | -2.38% | -1.88 | 1/3 | 1.863 | 8.57u | 0.598 | 0.962 | NO — TEST |
| Bundesliga | AH1 Favorite Line Steam | 193 | -11.04% | 142 | -13.88% | -19.72 | 0/3 | 1.972 | 21.24u | 0.962 | 0.962 | NO |
| Bundesliga | AH2 Favorite Price Steam, same line | 90 | +1.91% | 61 | -10.47% | -6.39 | 0/3 | 1.853 | 7.17u | 0.820 | 0.962 | NO — TEST |
| Ligue 1 | AH1 Favorite Line Steam | 257 | -3.85% | 162 | -9.12% | -14.78 | 1/3 | 1.992 | 23.89u | 0.889 | 0.962 | NO |
| Ligue 1 | AH2 Favorite Price Steam, same line | 92 | +2.34% | 64 | -7.22% | -4.62 | 0/3 | 1.865 | 7.76u | 0.732 | 0.962 | NO — TEST |

## Robustness checks

### AH1 — stricter line move >=0.50 goals

The stricter samples are tiny in most leagues and do not rescue the rule. TEST ROI remains negative in Premier League, La Liga, Bundesliga and Ligue 1; Serie A has only 4 observations and is not interpretable.

### AH2 — nearby no-vig thresholds

TEST ROI at 0.02 / 0.03 / 0.04:

- Premier League: **−8.13% / +4.76% / +14.96%** — primary positive result is not robust to the lower nearby threshold and TRAIN is negative.
- La Liga: **−5.13% / −2.64% / −6.09%**.
- Serie A: **−4.55% / −2.38% / −15.36%**.
- Bundesliga: **−10.92% / −10.47% / −17.00%**.
- Ligue 1: **+0.06% / −7.22% / −7.86%**.

## Decision

- No Stage64 forward watcher is created.
- No new R-rule is created.
- Asian handicap market movement is rejected in the tested preregistered form.
- R1/R2/R3 remain unchanged.
- Stage61 (АПЛ 1X2 steam), Stage62 (Бундеслига ТБ(2.5) steam) and Stage63 (ОЗ prospective capture) remain separate research layers.
