#!/usr/bin/env python3
"""Stage74/75 bridge: expose validated probability/value state through the app API.

This wrapper extends Stage74 without changing strategy eligibility, stakes or
football-data collection. It reads only the Stage72 SQLite projection.
"""
from __future__ import annotations

import stage74_app_api as app

_ORIG_PERFORMANCE = app.performance_payload
_ORIG_MATCH = app.aggregate_match


def _probability_docs(conn):
    rankings = app.base.state_doc(conn, 'probability_rankings.json') or {}
    performance = app.base.state_doc(conn, 'probability_performance.json') or {}
    meta = app.base.state_doc(conn, 'stage75_last_run.json') or {}
    return rankings, performance, meta


def performance_payload():
    status, payload = _ORIG_PERFORMANCE()
    with app.base.connect() as conn:
        rankings, probability_performance, meta = _probability_docs(conn)
    active = str(rankings.get('status') or '').upper() == 'OK'
    max_probability = rankings.get('max_probability') or []
    best_value = rankings.get('best_value') or []
    payload['probability_module'] = {
        'status': 'ACTIVE_FORWARD_MONITORING' if active else 'NOT_READY',
        'model_version': rankings.get('model_version') or meta.get('model_version'),
        'max_probability_ranking_available': bool(max_probability),
        'value_ranking_available': bool(best_value),
        'max_probability': max_probability,
        'best_value': best_value,
        'forward_performance': probability_performance,
        'stage75_meta': meta,
        'policy': {
            'canonical_only': True,
            'watch_excluded': True,
            'stake_changes': False,
            'predictions_frozen_prematch': True,
            'historical_backfill': 'FORBIDDEN',
            'paper_execution_is_not_proof_real_bet': True,
        },
    }
    return status, payload


def aggregate_match(fixture_id):
    status, payload = _ORIG_MATCH(fixture_id)
    if status != 200:
        return status, payload
    with app.base.connect() as conn:
        predictions = app.fixture_rows(conn, 'probability_predictions', fixture_id)
        rankings, _, _ = _probability_docs(conn)
    ranking_rows = []
    seen = set()
    for group in ('max_probability', 'best_value'):
        for row in rankings.get(group) or []:
            if str(row.get('api_fixture_id') or '') != str(fixture_id):
                continue
            key = (str(row.get('rule') or ''), str(row.get('api_fixture_id') or ''), str(row.get('selection') or ''))
            if key in seen:
                continue
            seen.add(key)
            ranking_rows.append(row)
    payload['probability'] = {
        'predictions': predictions,
        'active_rankings': ranking_rows,
        'strategy_mutation': False,
        'stake_changes': False,
    }
    return status, payload


app.performance_payload = performance_payload
app.aggregate_match = aggregate_match
app.Handler.server_version = 'PBKAppAPI/1.5'


if __name__ == '__main__':
    app.main()
