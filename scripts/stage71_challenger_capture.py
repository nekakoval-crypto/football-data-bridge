#!/usr/bin/env python3
"""Stage 71 prospective R1/R2 challenger capture across the locked league scope.

Research-only. It never writes canonical forward files.

- Freezes the first complete Bet365 1X2 snapshot captured for upcoming fixtures.
- Evaluates the exact R1 analogue in non-Serie-A leagues.
- Evaluates the exact R2 analogue only close to kickoff, using completed current-
  season league matches before the fixture.
- Captures Marathonbet away-win price only when a new research signal is created.
- Settles the separate research ledger from API-Football final results.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit

OPS = Path(os.getenv("OPS_DIR", "ops"))
CATALOG = OPS / "stage71_league_catalog.csv"
TRIGGERS = OPS / "stage71_research_trigger_ledger.csv"
FORWARD = OPS / "stage71_challenger_forward.csv"
META = OPS / "stage71_capture_last_run.json"
SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))
NEXT_PER_LEAGUE = int(os.getenv("STAGE71_NEXT_PER_LEAGUE", "5"))
R2_FREEZE_HOURS = float(os.getenv("STAGE71_R2_FREEZE_HOURS", "12"))
BET365_ID = int(os.getenv("STAGE71_BET365_BOOKMAKER_ID", "8"))
MATCH_WINNER_BET_ID = int(os.getenv("STAGE71_MATCH_WINNER_BET_ID", "1"))

TRIGGER_FIELDS = [
    "api_fixture_id","captured_at_utc","country","league","api_league_id","kickoff_utc",
    "home_team_id","home_team","away_team_id","away_team","b365_home","b365_draw","b365_away",
    "api_update_utc","source","fixture_status_at_capture"
]
FORWARD_FIELDS = [
    "research_id","family","country","league","api_league_id","api_fixture_id","kickoff_utc",
    "home_team_id","home_team","away_team_id","away_team","selection","stake_u",
    "trigger_captured_at_utc","trigger_b365_home","trigger_b365_draw","trigger_b365_away",
    "home_played","away_played","home_last5_ppg","away_last5_ppg","eligibility_frozen_at_utc",
    "user_bookmaker","user_odds","user_price_captured_at_utc","status","result","final_home_goals",
    "final_away_goals","user_profit_u","settled_at_utc","notes"
]

def now_dt(): return datetime.now(timezone.utc).replace(microsecond=0)
def iso(dt): return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def parse_dt(v):
    try: return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception: return None
def fnum(v):
    try:
        x=float(str(v).strip()); return x if math.isfinite(x) else None
    except Exception: return None
def inum(v):
    try:return int(v)
    except Exception:return None
def read_csv(path):
    if not path.exists(): return []
    with path.open(encoding="utf-8-sig", newline="") as f:return list(csv.DictReader(f))
def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    temp.replace(path)

def points(hg, ag):
    if hg is None or ag is None:return (None,None)
    if hg>ag:return (3,0)
    if hg<ag:return (0,3)
    return (1,1)
def team_state_before(completed, cutoff, home_id, away_id):
    hist=defaultdict(list)
    for x in completed:
        fx=x.get("fixture",{}) or {}; dt=parse_dt(fx.get("date"))
        if not dt or dt>=cutoff or (fx.get('status') or {}).get('short') != 'FT': continue
        teams=x.get("teams",{}) or {}; goals=x.get("goals",{}) or {}
        hid=inum((teams.get("home") or {}).get("id")); aid=inum((teams.get("away") or {}).get("id"))
        hg=inum(goals.get("home")); ag=inum(goals.get("away")); hp,ap=points(hg,ag)
        if hid is not None and hp is not None: hist[hid].append((dt,hp))
        if aid is not None and ap is not None: hist[aid].append((dt,ap))
    def one(tid):
        rr=sorted(hist.get(tid,[]), key=lambda z:z[0]); vals=[p for _,p in rr]
        return len(vals), (sum(vals[-5:])/len(vals[-5:]) if vals else None)
    return one(home_id), one(away_id)
def r1_from_trigger(t):
    h,d,a=fnum(t.get("b365_home")),fnum(t.get("b365_draw")),fnum(t.get("b365_away"))
    return bool(h and d and a and a<h and a<d and 1.20<=a<2.10)
def marathon_away_price(fixture_id, bet_id, home, away):
    d=s53.api_get("/odds", {"fixture":fixture_id,"bet":bet_id})
    prices=s53.unpack_matchwinner(d or {}, home, away)
    cand=[(odd,upd) for sel,odd,bm,upd in prices if sel=="away" and str(bm).strip().lower()=="marathonbet" and odd > 1]
    if not cand:return None,""
    return max(cand, key=lambda z:z[0])
def settle_rows(rows, completed_by_league, now):
    settled=0; result_maps={}
    for lid, comp in completed_by_league.items():
        m={}
        for x in comp:
            fx=x.get("fixture",{}) or {}; fid=str(fx.get("id") or ""); goals=x.get("goals",{}) or {}
            m[fid]=(inum(goals.get("home")), inum(goals.get("away")), str((fx.get("status") or {}).get("short") or ""), parse_dt(fx.get('date')))
        result_maps[str(lid)]=m
    for r in rows:
        if str(r.get("status") or "").upper()!="PENDING":continue
        ko=parse_dt(r.get("kickoff_utc"))
        if not ko or now<=ko:continue
        hit=result_maps.get(str(r.get("api_league_id") or ""),{}).get(str(r.get("api_fixture_id") or ""))
        if not hit:continue
        hg,ag,st,current_ko=hit
        if not current_ko or now <= current_ko:continue
        captured = parse_dt(r.get('trigger_captured_at_utc'))
        frozen = parse_dt(r.get('eligibility_frozen_at_utc'))
        priced = parse_dt(r.get('user_price_captured_at_utc'))
        if not captured or not frozen or max(captured, frozen) >= min(ko, current_ko):continue
        if r.get('user_odds') and (not priced or priced >= min(ko, current_ko)):continue
        if st!="FT" or hg is None or ag is None or hg < 0 or ag < 0:continue
        won=ag>hg; r["status"]="SETTLED"; r["result"]="W" if won else "L"
        r["final_home_goals"]=hg; r["final_away_goals"]=ag; r["settled_at_utc"]=iso(now)
        o=fnum(r.get("user_odds")); r["user_profit_u"]="" if o is None else f"{(o-1.0 if won else -1.0):.3f}"; settled+=1
    return settled

def run_capture(state, budget):
    now = now_dt()
    catalog = read_csv(CATALOG)
    scope = json.loads(Path('config/pbk_competition_scope.json').read_text(encoding='utf-8'))
    locked = {(r['country'], r['league']) for r in scope['core_big5'] + scope['extended_final_scope']}
    if len(locked) != 16 or len(catalog) != 16 or len({r.get('api_league_id') for r in catalog}) != 16 or {(r['country'], r['league']) for r in catalog} != locked or any(not r.get('api_league_id') for r in catalog):
        raise RuntimeError('Locked 16-league catalog incomplete or changed')
    triggers, forward = read_csv(TRIGGERS), read_csv(FORWARD)
    if audit.duplicates(triggers, forward):
        raise RuntimeError('Duplicate ledger keys; refusing automatic repair')
    trig_by_id = {r['api_fixture_id']: r for r in triggers}
    existing_ids = {r['research_id'] for r in forward}
    for t in triggers:
        item = state.setdefault('fixtures', {}).setdefault(t['api_fixture_id'], {
            'first_seen_at_utc': t['captured_at_utc'], 'kickoff_utc': t['kickoff_utc'],
            'api_league_id': t['api_league_id']})
        item.setdefault('r1_qualifies', r1_from_trigger(t) and audit.clean_trigger(t))
    for row in forward:
        if row['family'] == 'R2' and row['api_fixture_id'] in state['fixtures']:
            state['fixtures'][row['api_fixture_id']].setdefault('r2_evaluated_at_utc', row['eligibility_frozen_at_utc'])
    warnings, scans = [], []
    new_triggers = new_r1 = new_r2 = odds_calls = marathon_calls = 0
    research_catalog = [r for r in catalog if r['league'] != 'Serie A']
    live, completed_by_league, candidate_ids = {}, {}, set()
    # A single season inventory replaces next=5 AND the separate FT history call.
    # Fetch all inventories before spending quota on odds; no stale cache capture.
    for lg in research_catalog:
        lid = lg['api_league_id']
        try:
            data = s53.api_get('/fixtures', {'league': lid, 'season': SEASON, 'timezone': 'UTC'})
            fixtures = data['response']
            if not fixtures:
                raise RuntimeError('Empty season inventory; completeness unknown')
            if any(str((x.get('league') or {}).get('id')) != lid for x in fixtures):
                raise RuntimeError('Fixture league identity mismatch')
            if len({str(x['fixture']['id']) for x in fixtures}) != len(fixtures):
                raise RuntimeError('Duplicate fixture IDs in inventory')
            audit.remember(state, fixtures, now)
            completed_by_league[lid] = [x for x in fixtures if (x['fixture'].get('status') or {}).get('short') == 'FT']
            live.update({str(x['fixture']['id']): x for x in fixtures})
            upcoming = sorted([x for x in fixtures if audit.pregame(x, now)], key=lambda x: parse_dt(x['fixture']['date']))
            due = [x for x in upcoming if (parse_dt(x['fixture']['date'])-now).total_seconds() <= 86400]
            candidate_ids.update(str(x['fixture']['id']) for x in upcoming[:NEXT_PER_LEAGUE] + due)
            scans.append({'league': lg['league'], 'expected': len(due), 'scanned': len(due),
                          'legacy_next5_omitted': max(0, len(due)-NEXT_PER_LEAGUE), 'inventory': 'COMPLETE'})
        except Exception as exc:
            warnings.append(f"{lg['league']}: inventory unavailable: {exc}")
            scans.append({'league': lg['league'], 'inventory': 'UNKNOWN', 'expected': None, 'scanned': 0})
    # Retry missing pending fixtures (including previous seasons) fairly, in one bounded batch.
    missing = {r['api_fixture_id'] for r in forward if r['status'] == 'PENDING' and r['api_fixture_id'] not in live}
    retry = state.setdefault('retry', {})
    selected = sorted(missing, key=lambda fid: (retry.get(fid, ''), fid))[:20]
    if selected:
        for fid in selected:
            retry[fid] = iso(now)
        try:
            fixtures = s53.api_get('/fixtures', {'ids': '-'.join(selected), 'timezone': 'UTC'})['response']
            fixtures = [x for x in fixtures if str((x.get('fixture') or {}).get('id')) in selected]
            audit.remember(state, fixtures, now)
            live.update({str(x['fixture']['id']): x for x in fixtures})
        except Exception as exc:
            warnings.append(f'Pending fixture retry failed: {exc}')
    catalog_by_id = {r['api_league_id']: r for r in research_catalog}
    candidates = sorted([x for fid, x in live.items() if fid in candidate_ids and audit.pregame(x, now)],
                        key=lambda x: parse_dt(x['fixture']['date']))
    for x in candidates:
        fx = x['fixture']; fid = str(fx['id']); lid = str(x['league']['id'])
        if lid not in catalog_by_id:
            continue
        lg = catalog_by_id[lid]
        item = state['fixtures'][fid]
        if fid not in trig_by_id:
            home, away = x['teams']['home'], x['teams']['away']
            try:
                odds_calls += 1
                fresh = s53.get_bet365_prices(fid, BET365_ID, MATCH_WINNER_BET_ID, home['name'], away['name'])
                captured_now = now_dt()
                values = [fnum(fresh.get(k, (None, '', ''))[0]) for k in ('home', 'draw', 'away')]
                updates = [fresh.get(k, (None, '', ''))[2] for k in ('home', 'draw', 'away')]
                if not audit.pregame(x, captured_now) or any(u and (not audit.dt(u) or audit.dt(u) > captured_now) for u in updates):
                    item['capture_reason'] = 'not_clean_pregame_at_response'
                    continue
                if not all(v is not None and v > 1 for v in values):
                    item['capture_reason'] = 'complete_Bet365_odds_unavailable'
                    continue
                tr = dict(api_fixture_id=fid, captured_at_utc=iso(captured_now), country=lg['country'],
                          league=lg['league'], api_league_id=lid, kickoff_utc=fx['date'],
                          home_team_id=home['id'], home_team=home['name'], away_team_id=away['id'], away_team=away['name'],
                          b365_home=values[0], b365_draw=values[1], b365_away=values[2],
                          api_update_utc=max(updates), source='Stage71 first complete Bet365 1X2 capture',
                          fixture_status_at_capture='NS')
                triggers.append(tr); trig_by_id[fid] = tr; new_triggers += 1
                # Persist opener before execution request, so interrupted runs never replace it.
                write_csv(TRIGGERS, TRIGGER_FIELDS, triggers)
            except Exception as exc:
                item['capture_reason'] = 'odds_error_or_budget; retry_required'
                warnings.append(f'{fid}: Bet365 capture failed: {exc}')
                continue
        t = trig_by_id[fid]
        if not audit.clean_trigger(t):
            item['capture_reason'] = 'invalid_trigger_provenance'
            continue
        ko = parse_dt(fx['date'])
        # Preserve frozen kickoff/eligibility and expose changed schedule separately.
        # A moved opener cannot create a fresh R2 observation using a changed history.
        if ko != parse_dt(t['kickoff_utc']):
            item['capture_reason'] = 'rescheduled_trigger; manual_research_review'
            continue
        if not r1_from_trigger(t):
            item['r1_qualifies'] = False
            continue
        item['r1_qualifies'] = True
        hid, aid = inum(t['home_team_id']), inum(t['away_team_id'])
        captured_now = now_dt()
        (hp, hppg), (ap, appg) = team_state_before(completed_by_league.get(lid, []), captured_now, hid, aid)
        hrs = (ko-captured_now).total_seconds()/3600
        r2_ok = hp >= 5 and ap >= 5 and hppg is not None and appg is not None and appg > hppg
        if 0 < hrs <= R2_FREEZE_HOURS and lid in completed_by_league:
            item['r2_evaluated_at_utc'] = iso(captured_now)
            item['r2_qualifies'] = r2_ok
        rid, rid2 = f'R1|{lid}|{fid}', f'R2|{lid}|{fid}'
        new_r1_needed = rid not in existing_ids
        new_r2_needed = 0 < hrs <= R2_FREEZE_HOURS and r2_ok and rid2 not in existing_ids and lid in completed_by_league
        if not new_r1_needed and not new_r2_needed:
            continue
        try:
            marathon_calls += 1
            user_odd, update = marathon_away_price(fid, MATCH_WINNER_BET_ID, t['home_team'], t['away_team'])
        except Exception as exc:
            warnings.append(f'{fid}: execution price retry required: {exc}')
            continue
        captured_now = now_dt()
        if not audit.pregame(x, captured_now) or update and (not audit.dt(update) or audit.dt(update) > captured_now):
            warnings.append(f'{fid}: execution response not clean pre-kickoff')
            continue
        base={"country":t.get("country") or "","league":t.get("league") or "","api_league_id":lid,"api_fixture_id":fid,"kickoff_utc":t.get("kickoff_utc") or "","home_team_id":t.get("home_team_id") or "","home_team":t.get("home_team") or "","away_team_id":t.get("away_team_id") or "","away_team":t.get("away_team") or "","selection":"П2","stake_u":"1.000","trigger_captured_at_utc":t.get("captured_at_utc") or "","trigger_b365_home":t.get("b365_home") or "","trigger_b365_draw":t.get("b365_draw") or "","trigger_b365_away":t.get("b365_away") or "","home_played":hp,"away_played":ap,"home_last5_ppg":"" if hppg is None else f"{hppg:.3f}","away_last5_ppg":"" if appg is None else f"{appg:.3f}","user_bookmaker":"Marathonbet","user_odds":"" if user_odd is None else user_odd,"user_price_captured_at_utc":iso(captured_now) if user_odd is not None else "","status":"PENDING","result":"","final_home_goals":"","final_away_goals":"","user_profit_u":"","settled_at_utc":""}
        if new_r1_needed:
            row=dict(base);row.update({"research_id":rid,"family":"R1","eligibility_frozen_at_utc":iso(captured_now),"notes":"research-only exact R1 analogue; never canonical automatically"});forward.append(row);existing_ids.add(rid);new_r1+=1
        if new_r2_needed:
            row=dict(base);row.update({"research_id":rid2,"family":"R2","eligibility_frozen_at_utc":iso(captured_now),"notes":"research-only exact R2 analogue frozen close to kickoff; never canonical automatically"});forward.append(row);existing_ids.add(rid2);new_r2+=1
        write_csv(FORWARD, FORWARD_FIELDS, forward)
    # Use official live inventory, not a result inferred from elapsed time.
    results = defaultdict(list)
    for x in live.values():
        results[str(x['league']['id'])].append(x)
    for row in forward:
        current = live.get(row['api_fixture_id'])
        if current and parse_dt(current['fixture']['date']) != parse_dt(row['kickoff_utc']):
            state['fixtures'][row['api_fixture_id']]['rescheduled'] = True
    settled = settle_rows(forward, results, now_dt())
    write_csv(TRIGGERS, TRIGGER_FIELDS, triggers)
    write_csv(FORWARD, FORWARD_FIELDS, forward)
    return dict(run_at_utc=iso(now_dt()), status='ATTENTION' if warnings else 'OK',
                research_leagues=len(research_catalog), new_triggers=new_triggers, new_r1_rows=new_r1,
                new_r2_rows=new_r2, settled_rows=settled, trigger_rows=len(triggers), forward_rows=len(forward),
                api_calls=budget.calls, odds_calls=odds_calls, marathon_calls=marathon_calls,
                scan=scans, warnings=warnings,
                canonical_captured=sum(r.get('rule') in {'R1', 'R2'} for r in read_csv(OPS/'user_forward_view.csv')))


def main():
    OPS.mkdir(parents=True, exist_ok=True)
    state_path = OPS / 'stage71_observation_state.json'
    # Exclusive local writer; workflow concurrency also serializes remote publication.
    lock = OPS / 'stage71_capture.lock'
    with lock.open('x'):
        pass
    original = s53.api_get
    try:
        state = audit.read(state_path)
        budget = audit.Budget(original, state, now_dt(),
                              int(os.getenv('STAGE71_MAX_API_CALLS', '60')),
                              int(os.getenv('STAGE71_MAX_DAILY_API_CALLS', '180')),
                              checkpoint=lambda data: audit.save(state_path, data))
        s53.api_get = budget
        meta = {'run_at_utc': iso(now_dt()), 'status': 'ERROR', 'warnings': ['Capture interrupted']}
        try:
            meta = run_capture(state, budget)
        except Exception as exc:
            meta['warnings'] = [str(exc)]
            raise
        finally:
            meta['api_calls'] = budget.calls
            audit.save(state_path, state)
            audit.save(META, meta)
            audit.save(OPS / 'stage71_observation_health.json', audit.report(
                read_csv(TRIGGERS), read_csv(FORWARD), state, now_dt(), meta))
    finally:
        s53.api_get = original
        lock.unlink()
    print(json.dumps({k: v for k, v in meta.items() if k != 'scan'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
