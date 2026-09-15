# Player Grade limitations

`PBK_PLAYER_GRADE_V1` is not a traditional editorial match rating and does not claim to reproduce a proprietary club-grade product.

The API-Football aggregate tier is intentionally conservative: it cannot see true progressive passes/carries, pressure events, off-ball positioning or full action context, so Progression is a proxy and Pressing remains unavailable. Missing components reduce confidence rather than being scored as zero.

The StatsBomb Open Data event tier is a transparent research prototype that assigns individual event scores on a -2..+2 half-step scale. Its weights and mappings require forward validation before any promotion into PBK modelling.

Neither tier may alter canonical probability, Value eligibility, R1/R2/R3 admission, stake sizing or settlement.