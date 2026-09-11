#!/usr/bin/env python3
"""Zero-API Stage71 health, provenance guards and durable retry state."""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def dt(value):
    try:
        value = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return value.astimezone(timezone.utc) if value.tzinfo else None
    except (ValueError, TypeError):
        return None


def stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def read(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def clean_trigger(row):
    captured, kickoff = dt(row.get('captured_at_utc')), dt(row.get('kickoff_utc'))
    update = dt(row.get('api_update_utc'))
    return bool(captured and kickoff and captured < kickoff and
                (not row.get('api_update_utc') or update and update <= captured) and
                (row.get('fixture_status_at_capture') or 'NS') == 'NS')


def pregame(fixture, now):
    fx = fixture.get('fixture') or {}
    kickoff = dt(fx.get('date'))
    goals = fixture.get('goals') or {}
    score = (fixture.get('score') or {}).get('fulltime') or {}
    return bool(kickoff and now < kickoff and
                (fx.get('status') or {}).get('short') == 'NS' and
                all(v is None for v in [goals.get('home'), goals.get('away'),
                                        score.get('home'), score.get('away')]))


def duplicates(triggers, forward):
    def excess(keys):
        return sum(n - 1 for n in Counter(keys).values() if n > 1)
    return excess((r.get('api_league_id'), r.get('api_fixture_id')) for r in triggers) + max(
        excess(r.get('research_id') for r in forward),
        excess((r.get('family'), r.get('api_league_id'), r.get('api_fixture_id')) for r in forward))


class Budget:
    """Counts attempted calls, including failures, before issuing requests."""
    def __init__(self, get, state, now, limit=60, daily_limit=180, checkpoint=None):
        self.get, self.state, self.limit, self.daily_limit = get, state, limit, daily_limit
        self.calls = 0
        self.checkpoint = checkpoint
        day = now.date().isoformat()
        if state.get('api_day') != day:
            state.update(api_day=day, api_day_calls=0)

    def __call__(self, path, params=None):
        if self.calls >= self.limit or self.state['api_day_calls'] >= self.daily_limit:
            raise RuntimeError('Stage71 API budget exhausted; retry next run')
        self.calls += 1
        self.state['api_day_calls'] += 1
        if self.checkpoint:
            self.checkpoint(self.state)
        data = self.get(path, params)
        if not isinstance(data, dict) or data.get('errors') or not isinstance(data.get('response'), list):
            raise RuntimeError('Missing/invalid API response (including missing credentials)')
        if int((data.get('paging') or {}).get('total', 1)) > 1:
            raise RuntimeError('Incomplete paginated response; no clean evaluation')
        return data


def remember(state, fixtures, now):
    known = state.setdefault('fixtures', {})
    for x in fixtures:
        fx = x.get('fixture') or {}
        fid = str(fx.get('id') or '')
        if not fid:
            continue
        item = known.setdefault(fid, {'first_seen_at_utc': stamp(now)})
        old = item.get('kickoff_utc')
        new = fx.get('date')
        if old and dt(old) != dt(new):
            item['rescheduled'] = True
        item.update(kickoff_utc=new, fixture_status=(fx.get('status') or {}).get('short'),
                    api_league_id=str((x.get('league') or {}).get('id') or ''),
                    last_seen_at_utc=stamp(now))


def report(triggers, forward, state, now, meta=None):
    meta = meta or {}
    known = state.get('fixtures', {})
    by_trigger = {r['api_fixture_id']: r for r in triggers}
    risks = []
    for fid, x in known.items():
        kickoff = dt(x.get('kickoff_utc'))
        first = dt(x.get('first_seen_at_utc'))
        if not kickoff or not first or first >= kickoff:
            continue  # historical inventory is not a prospective expectation
        if x.get('fixture_status') in {'CANC', 'PST'}:
            continue
        t = by_trigger.get(fid)
        if kickoff <= now and not t:
            risks.append({'fixture_id': fid, 'reason': 'kickoff_passed_without_trigger; qualification_unknown'})
        elif kickoff <= now and x.get('r1_qualifies') and not x.get('r2_evaluated_at_utc'):
            risks.append({'fixture_id': fid, 'reason': 'R2_window_missed; qualification_unknown'})
        elif x.get('capture_reason') in {'invalid_trigger_provenance', 'rescheduled_trigger; manual_research_review', 'not_clean_pregame_at_response'}:
            risks.append({'fixture_id': fid, 'reason': x['capture_reason']})
        elif kickoff > now and (kickoff - now).total_seconds() <= 86400 and not t:
            risks.append({'fixture_id': fid, 'reason': x.get('capture_reason', 'awaiting_odds_scan')})
    ids = {r.get('research_id') for r in forward}
    for t in triggers:
        if not clean_trigger(t):
            risks.append({'fixture_id': t['api_fixture_id'], 'reason': 'invalid_trigger_provenance'})
    for fid, x in known.items():
        for family in ('R1', 'R2'):
            if x.get(family.lower() + '_qualifies') and f"{family}|{x['api_league_id']}|{fid}" not in ids:
                risks.append({'fixture_id': fid, 'reason': family + '_qualified_not_captured'})
    pending = [r for r in forward if r.get('status') == 'PENDING']
    stale = [r for r in pending if dt(known.get(r['api_fixture_id'], {}).get('kickoff_utc') or r.get('kickoff_utc')) and
             (now - dt(known.get(r['api_fixture_id'], {}).get('kickoff_utc') or r['kickoff_utc'])).total_seconds() > 48*3600]
    scans = meta.get('scan', [])
    dup = duplicates(triggers, forward)
    counts = dict(expected=sum(s.get('expected') or 0 for s in scans) if scans and all(s.get('inventory') == 'COMPLETE' for s in scans) else None,
                  scanned=sum(s.get('scanned', 0) for s in scans), captured=len(forward),
                  missed_or_at_risk=len({r['fixture_id'] for r in risks}), pending=len(pending),
                  stale=len(stale), rescheduled=sum(bool(x.get('rescheduled')) for x in known.values()),
                  cancelled=sum(x.get('fixture_status') == 'CANC' for x in known.values()),
                  settled=sum(r.get('status') == 'SETTLED' for r in forward), duplicates=dup)
    return {'run_at_utc': stamp(now), 'status': 'ATTENTION' if risks or dup or stale or meta.get('warnings') or not scans or counts['cancelled'] or counts['rescheduled'] else 'OK',
            'counts': counts, 'risks': risks, 'stale_ids': [r['research_id'] for r in stale],
            'scan': scans, 'warnings': meta.get('warnings', []),
            'scope': '16 locked leagues; 15 research writers; Serie A canonical read-only, completeness not certified',
            'canonical_captured': meta.get('canonical_captured'),
            'definitions': {'expected': 'scheduled NS fixtures in next 24h, not inferred qualifying bets',
                            'scanned': 'those fixtures evaluated for capture using a fresh complete league inventory',
                            'captured': 'all persisted R1/R2 research rows; counts use different units',
                            'missed_or_at_risk': 'unique observed fixtures with gaps; not a claim of known qualification'},
            'completeness': 'Only provider-visible fixtures/odds can be audited. Missing inventory, outages, quota and late odds prevent an unconditional guarantee.',
            'legacy_max_schedule_gap_hours': 18, 'schedule_gap_hours': 8, 'r2_freeze_hours': 12,
            'api_calls': meta.get('api_calls', 0), 'api_day_calls': state.get('api_day_calls', 0)}


def main():
    import stage71_challenger_capture as capture
    ops = Path(os.getenv('OPS_DIR', 'ops'))
    meta = read(ops / 'stage71_capture_last_run.json')
    result = report(capture.read_csv(ops / 'stage71_research_trigger_ledger.csv'),
                    capture.read_csv(ops / 'stage71_challenger_forward.csv'),
                    read(ops / 'stage71_observation_state.json'), datetime.now(timezone.utc), meta)
    save(ops / 'stage71_observation_health.json', result)
    print(json.dumps(result, ensure_ascii=False))
    if result['counts']['duplicates']:
        raise SystemExit('Duplicate ledger keys: refusing automatic repair')


if __name__ == '__main__':
    main()
