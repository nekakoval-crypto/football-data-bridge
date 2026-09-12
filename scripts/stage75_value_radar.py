"""Offline attention projection of frozen Stage75 predictions; never creates bets."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

PRIORITY = {'R2': 3, 'R1': 2, 'R3': 1}
LEVELS = ['STRONG_VALUE', 'WATCH_VALUE', 'MARKET_DISAGREEMENT', 'HIGH_PROB_LOW_VALUE']
POLICY = dict(research_only=True, watch_excluded=True, canonical_mutation=False,
              creates_signal=False, stake_changes=False, historical_backfill='FORBIDDEN',
              executable_bookmaker='Marathonbet')
EVENT_FIELDS = ['radar_id', 'model_version', 'radar_kind', 'first_crossed_at_utc',
                'api_fixture_id', 'kickoff_utc', 'home_team', 'away_team', 'selection',
                'primary_rule', 'source_rules', 'p_market_no_vig', 'p_pbk', 'p_market_pct',
                'p_pbk_pct', 'edge_pp', 'executable_odds', 'executable_bookmaker', 'ev',
                'ev_pct', 'probability_prediction_id', 'status', 'creates_signal',
                'stake_changes', 'source']


def number(value):
    try:
        value = Decimal(str(value))
        return value if value.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def instant(value):
    try:
        value = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return value if value.tzinfo else None
    except ValueError:
        return None


def classify(p_pbk, p_market, odds=None, bookmaker=None):
    """Decimal comparisons preserve inclusive boundaries without rounded thresholds."""
    pp, pm, od = map(number, (p_pbk, p_market, odds))
    if pp is None or pm is None or not (0 < pp < 1 and 0 < pm < 1):
        return None
    od = od if bookmaker == 'Marathonbet' and od is not None and od > 1 else None
    edge = pp - pm
    ev = pp * od - 1 if od is not None else None
    kinds = []
    if ev is not None and ev >= Decimal('.05') and edge >= Decimal('.03'):
        kinds = ['STRONG_VALUE']
        if od >= 2:
            kinds.append('LONGSHOT_STRONG')
    elif ev is not None and ev >= Decimal('.02') and edge >= Decimal('.02'):
        kinds = ['WATCH_VALUE']
    elif od is None and edge >= Decimal('.05'):
        kinds = ['MARKET_DISAGREEMENT']
    elif ev is not None and pp >= Decimal('.65') and ev < Decimal('.02'):
        kinds = ['HIGH_PROB_LOW_VALUE']
    return dict(kinds=kinds, p_pbk=float(pp), p_market_no_vig=float(pm),
                p_pbk_pct=float(pp*100), p_market_pct=float(pm*100), edge_pp=float(edge*100),
                executable_odds=float(od) if od is not None else None,
                executable_bookmaker='Marathonbet' if od is not None else None,
                ev=float(ev) if ev is not None else None,
                ev_pct=float(ev*100) if ev is not None else None)


def read_jsonl(path):
    if not path.exists():
        return b'', []
    raw = path.read_bytes()
    events = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    ids = [event['radar_id'] for event in events]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate Radar ids; ledger requires review')
    return raw, events


def atomic_write(path, raw):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def materialize(ops, forward, predictions, config, now):
    """Append first observations under an exclusive lock, retaining old bytes exactly."""
    ops = Path(ops)
    ops.mkdir(parents=True, exist_ok=True)
    lock = ops / '.stage75_value_radar.lock'
    handle = lock.open('x')
    try:
        with handle:
            return _materialize(ops, forward, predictions, config, now)
    finally:
        lock.unlink()


def _materialize(ops, forward, predictions, config, now):
    ledger = ops / 'stage75_value_radar.jsonl'
    original, events = read_jsonl(ledger)
    known = {event['radar_id']: event for event in events}
    added, items, groups = [], [], {}
    current_time = instant(now)
    if current_time is None:
        raise ValueError('Radar observation requires an aware timestamp')
    version = config['version']
    models = config.get('models', {})
    prediction_map = {(p.get('rule'), str(p.get('api_fixture_id')), p.get('selection')): p
                      for p in predictions if p.get('model_version') == version}
    for row in forward:
        rule = row.get('rule')
        if rule not in PRIORITY or row.get('status') not in {'PAPER', 'OPEN', 'REVIEW'}:
            continue
        if models.get(rule, {}).get('gate') != 'PASS' or row.get('result') or row.get('user_profit_u'):
            continue
        kickoff = instant(row.get('kickoff_utc'))
        key = (rule, str(row.get('api_fixture_id') or ''), row.get('selection'))
        p = prediction_map.get(key)
        if not p or not key[1] or not key[2] or not kickoff or current_time >= kickoff:
            continue
        times = [instant(p.get(field)) for field in ('created_at_utc', 'trigger_captured_at_utc')]
        if p.get('status') != 'FROZEN_PREMATCH' or any(t is None or t > current_time or t >= kickoff for t in times):
            continue
        if p.get('kickoff_utc') != row.get('kickoff_utc'):
            continue
        execution_time = instant(row.get('paper_user_execution_at_utc'))
        executable = (row.get('user_execution_status') == 'FROZEN' and execution_time is not None
                      and execution_time <= current_time and execution_time < kickoff)
        metrics = classify(p.get('p_pbk'), p.get('p_market_no_vig'),
                           row.get('paper_user_execution_odds') if executable else None,
                           row.get('paper_user_execution_bookmaker'))
        if metrics is None:
            continue
        groups.setdefault(key[1:], []).append((row, p, metrics))
    for key, rows in sorted(groups.items()):
        row, prediction, metrics = max(rows, key=lambda entry: PRIORITY[entry[0]['rule']])
        kinds = metrics.pop('kinds')
        if not kinds:
            continue
        item = {field: row.get(field) for field in ('api_fixture_id', 'kickoff_utc', 'home_team', 'away_team', 'selection')}
        item.update(metrics, primary_rule=row['rule'], source_rules=sorted({r[0]['rule'] for r in rows}),
                    model_version=version, probability_prediction_id=prediction['prediction_id'],
                    probability_status='HISTORICALLY_VALIDATED_FORWARD_MONITORING',
                    creates_signal=False, stake_changes=False, source='STAGE75_FROZEN_PREMATCH')
        for kind in kinds:
            radar_id = hashlib.sha256('|'.join((version, *key, kind)).encode()).hexdigest()[:24]
            if radar_id not in known:
                event = dict(item, radar_id=radar_id, radar_kind=kind,
                             first_crossed_at_utc=now, status='FIRST_CROSSING_FROZEN')
                known[radar_id] = event
                added.append(event)
        item.update(radar_level=kinds[0], radar_tags=[k for k in kinds if k == 'LONGSHOT_STRONG'],
                    first_crossed_at_utc_by_kind={e['radar_kind']: e['first_crossed_at_utc']
                        for e in known.values() if e['model_version'] == version
                        and str(e['api_fixture_id']) == key[0] and e['selection'] == key[1]})
        items.append(item)
    items.sort(key=lambda r: (LEVELS.index(r['radar_level']),
               -(r['ev_pct'] if r['ev_pct'] is not None else -1e99), -r['edge_pp'], r['kickoff_utc'], str(r['api_fixture_id']), r['selection']))
    if added or not ledger.exists():
        separator = b'\n' if original and not original.endswith(b'\n') else b''
        atomic_write(ledger, original + separator + b''.join(
            (json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False)+'\n').encode() for event in added))
    current = dict(generated_at_utc=now, status='OK', model_version=version,
                   scope='research-only frozen prematch probability/value', items=items, policy=POLICY)
    atomic_write(ops/'value_radar_current.json', json.dumps(current, ensure_ascii=False, indent=2, allow_nan=False).encode())
    return dict(radar_events_total=len(known), radar_events_created=len(added), radar_active_items=len(items))
