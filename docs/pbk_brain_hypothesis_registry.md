# PBK Brain — hypothesis registry

## Purpose

`config/pbk_hypothesis_registry.json` is the authoritative machine-readable inventory of PBK canonical strategies and research hypotheses. It exists so a requirement discussed in chat, a historical pattern, a player/context feature, or a market family cannot silently disappear from the project plan.

The registry is governance metadata only. Reading or editing it does **not** create a bet, change strategy eligibility, increase exposure, promote a WATCH idea, or alter the UI.

## UI freeze

While the Brain checklist is being built, `ui_freeze=true`. Work proceeds in this order:

1. unified hypothesis/strategy registry;
2. Historical Pattern / H2H Engine;
3. TRAIN → TEST → season stability → forward validation;
4. probability/value expansion across supported markets;
5. player/team grades and lineups;
6. cross-market Decision Engine;
7. only then resume visual/UI work.

## Lifecycle

Allowed statuses are:

`IDEA → DATA_READY → BACKTESTED → OOS_TESTED → FORWARD → CANONICAL`

`REJECTED` and `PAUSED` are terminal/administrative alternatives. Movement between states is manual and evidence-based; there is no automatic promotion.

`authority` is separate from status:

- `CANONICAL` — current locked betting strategy authority;
- `WATCH` — prospective observation, never extra canonical exposure;
- `RESEARCH` — hypothesis under study;
- `CONTEXT_ONLY` — evidence shown in the match passport but not a betting trigger by itself.

## Historical Pattern / H2H policy

Historical analysis is mandatory input to PBK Brain where data exists, but it is not treated as destiny.

The H2H engine must preserve venue orientation and report at minimum:

- same home team vs same away team, not a careless two-way H2H blend;
- sample size;
- recency;
- season spread/stability;
- comparison with each team's ordinary home/away baseline;
- market-relevant outcomes (1X2, goals/totals, BTTS and other supported markets when data exists).

A pattern such as a club repeatedly performing unusually well at home against a stronger named opponent is a research signal. It becomes important only if the database confirms that the matchup differs materially from the club's ordinary baseline and the sample/recency are visible. It never creates a bet on its own.

## Validation protocol

For hypotheses where betting performance can be measured, use the ordered protocol:

1. `TRAIN` — define the rule and parameters without peeking at the later test period;
2. `TEST` — untouched out-of-sample period;
3. `SEASON_STABILITY` — show whether the result is concentrated in one season;
4. `FORWARD` — immutable prospective capture using only information known before kickoff.

Metrics should include sample size, hit rate, ROI and max drawdown where applicable. Price-sensitive markets must use actual historical/executable prices; high win probability without price is not value.

## Locked canonical rules

The validator hard-locks R1/R2/R3 definitions and the 16-league competition scope. A registry PR fails if those definitions drift. Historical results are never inserted into the clean forward ledger.

## Brain families explicitly tracked

The first registry version intentionally includes canonical R1/R2/R3 plus historical H2H/home-away patterns, weekday/time, rest/schedule, cup/Europe load, season objective context, favourite/underdog price bands, totals, BTTS, team totals, executable half handicaps, Overall Grade, Player Importance, XI Quality, Rotation, Absence/Return Impact, referee, weather, CLV/market movement, all-market probability/value and the future cross-market Decision Engine.

Future ideas must receive a stable registry id instead of living only in chat or prose documentation.
