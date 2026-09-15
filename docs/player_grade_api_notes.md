# Player Grade API notes

The grading engine is intentionally separated from transport. Future read APIs should expose only stored/read-model evidence, never trigger provider calls.

Suggested additive Match Card section:

- `player_grade`: per-side starter grades, Form 5/10 and coverage/confidence;
- `xi_quality`: expected/official/current XI quality with by-line values;
- `manual_scenarios`: saved WHAT-IF scenarios for the selected fixture, if user-scoped persistence is available.

All sections must retain `research_only=true` and mutation flags false until a separately validated promotion decision.