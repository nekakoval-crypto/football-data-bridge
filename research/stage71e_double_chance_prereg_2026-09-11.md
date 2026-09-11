# Stage71E — Double Chance prospective market capture

Date locked: 2026-09-11
Status: PREREGISTERED / PROSPECTIVE DATA COLLECTION ONLY

## Why prospective only

The canonical `Football_Top5_2016-2026.csv` has no direct bookmaker-price columns for Double Chance. Therefore PBK will not derive 1Х / Х2 / 12 odds from 1X2 probabilities and then call those derived values executable historical prices.

Stage71E collects the real bookmaker market prospectively.

## Locked scope

Competitions: all 16 PBK locked national leagues.
Market: full-time regulation Double Chance only.
Selections:
- 1Х = home or draw
- Х2 = draw or away
- 12 = either team wins / no draw

Bookmakers:
- Bet365 = reference opener / movement / observed close
- Marathonbet = executable user-price snapshot where available

No global odds cap.

## Capture protocol

1. Discover the generic pre-match Double Chance market through `/odds/bets`, preferring an exact market-name match and rejecting half-specific/statistical markets.
2. Freeze the first complete Bet365 1Х / Х2 / 12 price triplet per fixture.
3. Track timestamped Bet365 + Marathonbet triplets inside the near-kickoff tracking horizon.
4. Convert a complete triplet to normalized no-vig probabilities only for movement analysis; bookmaker odds themselves remain stored unchanged.
5. Freeze the latest observed pre-kickoff exact Double Chance triplet as observed close after kickoff.
6. Never substitute 1X2-derived synthetic odds for a missing Double Chance bookmaker price.

## Governance

Stage71E raw capture creates zero betting signals and zero WATCH events.

A later discovery stage may select a hypothesis only from an initial frozen sample. Before a new independent holdout begins, that hypothesis must lock:
- league / league family;
- selection (1Х / Х2 / 12) or symmetric selection rule;
- movement/eligibility rule;
- price convention;
- stake and settlement;
- sample and promotion criteria.

The discovery sample cannot be reused as the independent holdout.

## Settlement

If a future candidate is approved for prospective validation:
- 1Х wins on home win or draw;
- Х2 wins on draw or away win;
- 12 wins on either home or away win and loses on draw.

Flat-stake convention must be locked before that validation.

## Relationship to Ф(0)

Double Chance is a separate market from Draw No Bet. Stage71D historical Ф(0) research cannot be transferred to Double Chance, and Stage71E capture does not rescue or modify the Stage71D result.
