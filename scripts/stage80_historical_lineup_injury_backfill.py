#!/usr/bin/env python3
"""Stage80 PBK16 historical lineup + adaptive injury backfill.

This stage builds RETROSPECTIVE historical evidence only.

Inputs:
- ops/pbk16_all_competition_fixture_history.csv

Outputs:
- ops/historical_lineup_snapshots.csv
- ops/historical_injury_snapshots.csv
- ops/stage80_historical_lineup_injury_backfill_state.csv
- ops/stage80_historical_lineup_injury_backfill_last_run.json

Provider access:
- only through the shared API-Football broker/budget layer
- successful real provider calls are archived by the shared raw archive layer

Temporal semantics:
- responses retrieved now for historical fixtures are retrospective evidence
- no PREMATCH_FROZEN authority is claimed
- no signal/probability/eligibility/stake/Forward Journal mutation

Policy:
- lineups: attempt all eligible PBK16 domestic league fixtures, newest first
- injuries: adaptive competition-season suppression after repeated exact NO_DATA
- CAPTURED and exact NO_DATA are terminal per fixture+endpoint
- ERROR remains retryable
- first quota marker stops the batch immediately
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
import stage77_player_stats_capture as current
from api_football_broker import ApiFootballBrokerError


OPS = Path(os.getenv("OPS_DIR", "ops"))
SOURCE = OPS / "pbk16_all_competition_fixture_history.csv"
LINEUPS = OPS / "historical_lineup_snapshots.csv"
INJURIES = OPS / "historical_injury_snapshots.csv"
STATE = OPS / "stage80_historical_lineup_injury_backfill_state.csv"
META = OPS / "stage80_historical_lineup_injury_backfill_last_run.json"
BUDGET_STATE = OPS / "stage80_historical_lineup_injury_budget_state.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

VERSION = "PBK_STAGE80_HISTORICAL_LINEUP_INJURY_BACKFILL_V1"
TERMINAL = {"FT", "AET", "PEN", "FINISHED"}
ENDPOINT_LINEUPS = "/fixtures/lineups"
ENDPOINT_INJURIES = "/injuries"

LINEUP_FIELDS = [
    "fixture_id",
    "country",
    "provider_competition_id",
    "competition_name",
    "season",
    "round",
    "kickoff_utc",
    "home_team",
    "away_team",
    "team_id",
    "team_name",
    "side",
    "formation",
    "coach_id",
    "coach_name",
    "starting_xi_json",
    "starting_xi_count",
    "substitutes_json",
    "substitutes_count",
    "retrieved_at_utc",
    "source_endpoint",
    "temporal_authority",
    "archive_version",
]

INJURY_FIELDS = [
    "fixture_id",
    "country",
    "provider_competition_id",
    "competition_name",
    "season",
    "round",
    "kickoff_utc",
    "home_team",
    "away_team",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "availability_type",
    "reason",
    "retrieved_at_utc",
    "source_endpoint",
    "temporal_authority",
    "archive_version",
]

STATE_FIELDS = [
    "fixture_id",
    "endpoint",
    "country",
    "provider_competition_id",
    "competition_name",
    "season",
    "round",
    "kickoff_utc",
    "home_team",
    "away_team",
    "attempt_count",
    "last_attempt_at_utc",
    "last_attempt_result",