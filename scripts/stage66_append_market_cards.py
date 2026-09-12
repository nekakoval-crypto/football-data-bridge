#!/usr/bin/env python3
"""Offline locked-league market/research projection; never creates signals."""
import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

OPS = Path(os.getenv('OPS_DIR', 'ops'))
# family, source, line dimensions, price suffixes, display labels, fixed league
LAYERS = [
    ('MATCH_WINNER', 'stage61_market_snapshots.csv', (), ('home','draw','away'), ('П1','Х','П2'), '39'),
    ('MATCH_WINNER', 'stage71_research_trigger_ledger.csv', (), ('home','draw','away'), ('П1','Х','П2'), ''),
    ('TOTAL', 'stage62_ou_snapshots.csv', (), ('over25','under25'), ('ТБ(2.5)','ТМ(2.5)'), '78'),
    ('BTTS', 'stage63_btts_snapshots.csv', (), ('yes','no'), ('ОЗ Да','ОЗ Нет'), ''),
    ('TEAM_TOTAL', 'stage71c_team_total_snapshots.csv', ('team_side','line'), ('over','under'), ('ИТБ','ИТМ'), ''),
    ('DOUBLE_CHANCE', 'stage71e_double_chance_snapshots.csv', (), ('1x','x2','12'), ('1Х','Х2','12'), ''),
    ('EUROPEAN_HANDICAP', 'stage71f_eh_snapshots.csv', ('home_handicap_line',), ('home','draw','away'), ('П1','Х','П2'), ''),
    ('DNB', 'stage71g_dnb_snapshots.csv', (), ('f1_0','f2_0'), ('Ф1(0)','Ф2(0)'), ''),
]
LABELS = dict(MATCH_WINNER='1X2', TOTAL='Тотал 2.5', BTTS='ОЗ', TEAM_TOTAL='ИТБ/ИТМ',
              DOUBLE_CHANCE='1Х/Х2/12', EUROPEAN_HANDICAP='Европейская фора', DNB='Ф(0)')

def read_csv(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}

def dt(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError): return None

def odd(value):
    try:
        n = float(value)
        return f'{n:g}' if math.isfinite(n) and n > 1 else 'нет данных'
    except (TypeError, ValueError): return 'нет данных'

def build_cards(ops=OPS, now=None):
    now = now or datetime.now(timezone.utc)
    catalog = {r['api_league_id']: r for r in read_csv(ops/'stage71_league_catalog.csv')}
    scope = read_json(Path(__file__).resolve().parents[1]/'config/pbk_competition_scope.json')
    locked = {(r['country'], r['league']) for r in scope['core_big5'] + scope['extended_final_scope']}
    catalog = {k:v for k,v in catalog.items() if (v['country'], v['league']) in locked}
    identities = {}
    grouped = defaultdict(dict)
    # Snapshots supply an immediate migration fallback before the first inventory capture.
    for family, filename, dims, suffixes, labels, fixed in LAYERS:
        for row in read_csv(ops/filename):
            fid = str(row.get('api_fixture_id') or '')
            lid = str(row.get('league_id') or row.get('api_league_id') or fixed)
            if not fid or lid not in catalog: continue
            stamp = dt(row.get('captured_at_utc'))
            if not stamp or stamp > now: continue
            if stamp >= (dt(identities.get(fid, {}).get('captured_at_utc')) or datetime.min.replace(tzinfo=timezone.utc)):
                identities[fid] = {**row, 'api_league_id':lid}
            key = (family,) + tuple(row.get(k, '') for k in dims)
            old = grouped[fid].get(key)
            if not old or stamp > dt(old[0]['captured_at_utc']):
                grouped[fid][key] = (row, suffixes, labels, filename)
    # Fixture inventory is independent of odds availability and has current status/kickoff.
    for row in read_json(ops/'market_research_fixtures.json').get('fixtures', []):
        fid = str(row.get('api_fixture_id') or '')
        if fid and str(row.get('api_league_id')) in catalog:
            identities[fid] = {**identities.get(fid, {}), **row}
    state = read_json(ops/'stage71_observation_state.json').get('fixtures', {})
    cards = []
    for fid, fx in identities.items():
        current = state.get(fid, {})
        if (dt(current.get('last_seen_at_utc')) or datetime.min.replace(tzinfo=timezone.utc)) > (dt(fx.get('captured_at_utc')) or datetime.min.replace(tzinfo=timezone.utc)):
            fx = {**fx, **{k:current[k] for k in ('kickoff_utc','fixture_status') if k in current}}
        kickoff = dt(fx.get('kickoff_utc'))
        if not kickoff or not now < kickoff <= now + timedelta(days=14): continue
        fixture_status = fx.get('fixture_status') or 'NS'
        if fixture_status not in ('NS', 'PST', 'CANC', 'SUSP', 'INT', 'TBD'): continue
        markets = []
        for key, (row, suffixes, labels, filename) in sorted(grouped[fid].items()):
            if fixture_status != 'NS': continue
            captured = dt(row['captured_at_utc'])
            # Never attach old prices to a rescheduled fixture or a post-kickoff capture.
            if dt(row.get('kickoff_utc')) != kickoff or captured >= kickoff: continue
            if row.get('fixture_status') not in (None, '', 'NS'): continue
            family = key[0]
            name = LABELS[family]
            if family == 'TEAM_TOTAL': name += f" {'1' if row.get('team_side') == 'H' else '2'} ({row.get('line')})"
            if family == 'EUROPEAN_HANDICAP': name += f" хозяев ({row.get('home_handicap_line')})"
            for prefix, book in [('b365_', 'Bet365'), ('user_', row.get('user_bookmaker') or 'Marathonbet')]:
                prices = [odd(row.get(prefix+s)) for s in suffixes]
                if all(p == 'нет данных' for p in prices): continue
                markets.append({'market':family, 'text':name+' · '+' | '.join(f'{label}: {price}' for label,price in zip(labels,prices))+' @ '+book,
                                'bookmaker':book, 'captured_at_utc':row['captured_at_utc'],
                                'api_update_utc':row.get('api_odds_update_utc') or row.get('api_update_utc') or '',
                                'source':filename, 'status':'COLLECTED_SNAPSHOT'})
        available = {r['market'] for r in markets}
        for family, label in LABELS.items():
            if family not in available: markets.append({'market':family, 'text':label+' — нет данных', 'status':'NO_DATA'})
        lg = catalog[str(fx['api_league_id'])]
        cards.append({'fixture_id':fid, 'league':lg['league'], 'league_id':lg['api_league_id'], 'country':lg['country'],
                      'home_team':fx.get('home_team') or 'нет данных', 'away_team':fx.get('away_team') or 'нет данных',
                      'kickoff_utc':fx['kickoff_utc'], 'kickoff_local':kickoff.strftime('%d.%m %H:%M UTC'),
                      'markets':markets, 'fixture_status':fixture_status, 'status':'MARKET_VIEW_ONLY', 'creates_signal':False})
    return sorted(cards, key=lambda c:(c['kickoff_utc'], c['league'], c['fixture_id']))

def main():
    path = OPS/'attention_board.json'
    if not path.exists(): return
    board = read_json(path)
    cards = build_cards()
    board['market_cards'] = cards
    board.setdefault('summary', {})['market_cards'] = len(cards)
    path.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding='utf-8')
    mdpath = OPS/'attention_board.md'
    md = mdpath.read_text(encoding='utf-8-sig') if mdpath.exists() else ''
    heading = '\n## 🧩 Рыночные карточки ближайших матчей\n'
    md = md.split(heading)[0] + heading + '> Собранные снимки рынков; не сигналы и не рекомендации.\n'
    for card in cards:
        md += f"\n- **{card['home_team']} — {card['away_team']}** | {card['league']} | {card['kickoff_local']}\n"
        for market in card['markets']: md += f"  - {market['text']}\n"
    mdpath.write_text(md, encoding='utf-8')
    print(json.dumps({'market_cards':len(cards), 'api_calls':0, 'creates_signals':False}))

if __name__ == '__main__': main()
