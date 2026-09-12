"""Persist identities from the existing shared fixture cache. No provider calls."""
import json

def persist(ops, cache, captured_at):
    fixtures = {}
    for key, payload in cache.items():
        if key[0] != '/fixtures': continue
        for row in (payload or {}).get('response', []):
            fx = row.get('fixture') or {}
            teams = row.get('teams') or {}
            fid = str(fx.get('id') or '')
            if not fid: continue
            fixtures[fid] = {'api_fixture_id':fid, 'api_league_id':str((row.get('league') or {}).get('id') or ''),
                             'kickoff_utc':fx.get('date'), 'fixture_status':(fx.get('status') or {}).get('short'),
                             'home_team':(teams.get('home') or {}).get('name'), 'away_team':(teams.get('away') or {}).get('name'),
                             'captured_at_utc':captured_at}
    path = ops/'market_research_fixtures.json'
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps({'captured_at_utc':captured_at, 'api_calls_added':0,
                                'fixtures':list(fixtures.values())}, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)
