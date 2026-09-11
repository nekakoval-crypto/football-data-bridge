# Stage71F — European Handicap 3-way prospective capture

Date locked: 2026-09-11
Status: PREREGISTERED / PROSPECTIVE DATA COLLECTION ONLY

## Why prospective only

The canonical `Football_Top5_2016-2026.csv` contains Asian Handicap fields but no direct Bet365 European / 3-way handicap price series. Asian Handicap prices must not be relabelled as European Handicap prices.

Stage71F therefore captures the real bookmaker market prospectively.

## Locked scope

Competitions: all 16 PBK locked national leagues.
Time settlement: full-time regulation.
Market family: European / 3-way handicap only.
Selections for each exact integer handicap line:
- Ф1(line)
- Х с форой(line)
- Ф2(line)

Bookmakers:
- Bet365 = reference opener / movement / observed close
- Marathonbet = executable user-price snapshot where available

No global odds cap. No post-hoc line selection.

## Safe market discovery

The capture may accept only a generic pre-match market explicitly named as `European Handicap`, `Handicap Result`, or an unambiguous equivalent with three-way settlement. It must reject:
- Asian Handicap;
- half-specific handicap markets;
- corners/cards/shots/offside handicap markets;
- two-way handicap markets.

If the provider cannot be mapped unambiguously, the stage fails rather than collecting a neighbouring market.

## Capture protocol

For every upcoming fixture in the locked universe:
1. Discover the safe generic pre-match 3-way handicap bet ID from `/odds/bets`.
2. Preserve every complete Bet365 integer line with all three selections Home / Draw / Away.
3. Freeze the first complete triplet for each fixture+line.
4. Track timestamped Bet365 and Marathonbet triplets near kickoff.
5. Store normalized no-vig three-way probabilities for movement analysis while preserving raw bookmaker prices.
6. Freeze the latest observed pre-kickoff exact same fixture+line triplet as observed close.
7. Never replace a missing line with a neighbouring line after result or kickoff.

## Governance

Raw Stage71F capture creates zero betting signals and zero WATCH events.

Any future candidate must be selected on a frozen discovery sample, then preregister line/direction/eligibility/price/stake/settlement before a new independent prospective holdout. Discovery data cannot be reused as the holdout.

## Relationship to Asian Handicap and Ф(0)

European Handicap is a separate 3-way market. Results from Stage64 Asian Handicap or Stage71D Ф(0) cannot be transferred to this market family.
