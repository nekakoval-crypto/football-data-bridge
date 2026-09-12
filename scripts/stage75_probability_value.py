#!/usr/bin/env python3
"""Stage75 — validated probability calibration + value rankings for canonical PBK signals.

No football API calls. Predictions are frozen from immutable Stage53 trigger odds.
The module cannot create strategy eligibility or alter stakes/thresholds.
"""
from __future__ import annotations
import csv, json, math, os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from stage75_value_radar import materialize as materialize_radar

OPS=Path(os.getenv('OPS_DIR','ops'))
CFG=Path(os.getenv('PBK_PROBABILITY_CONFIG','config/pbk_probability_models.json'))
FORWARD=OPS/'user_forward_view.csv';TRIGGERS=OPS/'trigger_ledger.csv'
LEDGER=OPS/'stage75_probability_predictions.csv';SETTLE=OPS/'stage75_probability_settlements.csv'
RANK=OPS/'probability_rankings.json';PERF=OPS/'probability_performance.json';META=OPS/'stage75_last_run.json'
PRED_FIELDS=['prediction_id','model_version','rule','api_fixture_id','kickoff_utc','home_team','away_team','selection','trigger_captured_at_utc','trigger_b365_home','trigger_b365_draw','trigger_b365_away','p_market_no_vig','p_pbk','model_alpha','created_at_utc','status']
SET_FIELDS=['prediction_id','rule','api_fixture_id','settled_at_utc','result','y','p_market_no_vig','p_pbk','brier_market','brier_pbk','logloss_market','logloss_pbk']

def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def read_csv(p):
    if not p.exists():return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_csv(p,fields,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def fnum(v):
    try:
        x=float(str(v).strip());return x if math.isfinite(x) else None
    except Exception:return None
def pct(v):return None if v is None else round(v*100,3)
def logit(p):
    p=min(max(p,1e-9),1-1e-9);return math.log(p/(1-p))
def logistic(x):return 1/(1+math.exp(-x))
def logloss(p,y):
    p=min(max(p,1e-12),1-1e-12);return -(y*math.log(p)+(1-y)*math.log(1-p))

def selected_probability(row,selection):
    h=fnum(row.get('b365_home'));d=fnum(row.get('b365_draw'));a=fnum(row.get('b365_away'))
    if not h or not d or not a:return None,(h,d,a)
    denom=1/h+1/d+1/a
    s=str(selection or '').upper()
    if s in {'AWAY','A','П2'}:raw=1/a
    elif s in {'DRAW','D','Х','X'}:raw=1/d
    elif s in {'HOME','H','П1'}:raw=1/h
    else:return None,(h,d,a)
    return raw/denom,(h,d,a)

def main():
    now=now_iso();cfg=json.loads(CFG.read_text(encoding='utf-8'));models=cfg.get('models') or {};model_version=cfg.get('version') or 'UNKNOWN'
    forward=read_csv(FORWARD);triggers=read_csv(TRIGGERS);preds=read_csv(LEDGER);settles=read_csv(SETTLE)
    trigger_by_fixture={str(r.get('api_fixture_id') or ''):r for r in triggers}
    pred_ids={r.get('prediction_id') for r in preds};settled_ids={r.get('prediction_id') for r in settles}
    created=0
    for r in forward:
        rule=str(r.get('rule') or '').strip();fid=str(r.get('api_fixture_id') or '').strip();selection=str(r.get('selection') or '').strip()
        model=models.get(rule)
        if not model or model.get('gate')!='PASS' or not fid:continue
        pid=f'{model_version}|{rule}|{fid}|{selection}'
        if pid in pred_ids:continue
        tr=trigger_by_fixture.get(fid)
        if not tr:continue
        pm,(h,d,a)=selected_probability(tr,selection)
        if pm is None:continue
        alpha=float(model['alpha']);pp=logistic(logit(pm)+alpha)
        preds.append({'prediction_id':pid,'model_version':model_version,'rule':rule,'api_fixture_id':fid,'kickoff_utc':r.get('kickoff_utc') or '','home_team':r.get('home_team') or tr.get('home_team') or '','away_team':r.get('away_team') or tr.get('away_team') or '','selection':selection,'trigger_captured_at_utc':tr.get('captured_at_utc') or '','trigger_b365_home':h,'trigger_b365_draw':d,'trigger_b365_away':a,'p_market_no_vig':f'{pm:.9f}','p_pbk':f'{pp:.9f}','model_alpha':f'{alpha:.9f}','created_at_utc':now,'status':'FROZEN_PREMATCH'})
        pred_ids.add(pid);created+=1
    write_csv(LEDGER,PRED_FIELDS,preds)

    forward_key={(str(r.get('rule') or ''),str(r.get('api_fixture_id') or ''),str(r.get('selection') or '')):r for r in forward}
    settled_new=0
    for p in preds:
        pid=p.get('prediction_id');key=(str(p.get('rule') or ''),str(p.get('api_fixture_id') or ''),str(p.get('selection') or ''))
        r=forward_key.get(key)
        if not r or r.get('status')!='SETTLED' or pid in settled_ids:continue
        profit=fnum(r.get('user_profit_u'))
        if profit is None or profit==0:continue
        y=1 if profit>0 else 0;pm=fnum(p.get('p_market_no_vig'));pp=fnum(p.get('p_pbk'))
        if pm is None or pp is None:continue
        settles.append({'prediction_id':pid,'rule':p.get('rule'),'api_fixture_id':p.get('api_fixture_id'),'settled_at_utc':now,'result':'WIN' if y else 'LOSS','y':y,'p_market_no_vig':f'{pm:.9f}','p_pbk':f'{pp:.9f}','brier_market':f'{(pm-y)**2:.9f}','brier_pbk':f'{(pp-y)**2:.9f}','logloss_market':f'{logloss(pm,y):.9f}','logloss_pbk':f'{logloss(pp,y):.9f}'})
        settled_ids.add(pid);settled_new+=1
    write_csv(SETTLE,SET_FIELDS,settles)

    # Active rankings join frozen probabilities to current executable paper price.
    pred_map={(str(p.get('rule')),str(p.get('api_fixture_id')),str(p.get('selection'))):p for p in preds}
    candidates=[]
    for r in forward:
        if r.get('status') not in {'PAPER','OPEN','REVIEW'}:continue
        key=(str(r.get('rule') or ''),str(r.get('api_fixture_id') or ''),str(r.get('selection') or ''));p=pred_map.get(key)
        if not p:continue
        pp=fnum(p.get('p_pbk'));pm=fnum(p.get('p_market_no_vig'));od=fnum(r.get('paper_user_execution_odds'))
        ev=(pp*od-1) if pp is not None and od is not None else None
        candidates.append({'rule':r.get('rule'),'api_fixture_id':r.get('api_fixture_id'),'kickoff_utc':r.get('kickoff_utc'),'home_team':r.get('home_team'),'away_team':r.get('away_team'),'selection':r.get('selection'),'p_market_no_vig':pm,'p_pbk':pp,'p_market_pct':pct(pm),'p_pbk_pct':pct(pp),'paper_user_odds':od,'paper_user_bookmaker':r.get('paper_user_execution_bookmaker'),'ev':ev,'ev_pct':pct(ev),'probability_status':'HISTORICALLY_VALIDATED_FORWARD_MONITORING'})
    # dedupe nested R1/R2 same fixture+selection; R2 is the more specific model.
    dedup={}
    priority={'R2':3,'R1':2,'R3':1}
    for c in candidates:
        k=(str(c['api_fixture_id']),str(c['selection']))
        if k not in dedup or priority.get(str(c['rule']),0)>priority.get(str(dedup[k]['rule']),0):dedup[k]=c
    unique=list(dedup.values())
    by_prob=sorted(unique,key=lambda x:(x['p_pbk'] is not None,x['p_pbk'] or -1),reverse=True)
    by_value=sorted(unique,key=lambda x:(x['ev'] is not None,x['ev'] or -999),reverse=True)
    for i,x in enumerate(by_prob,1):x['probability_rank']=i
    value_rank={(str(x['api_fixture_id']),str(x['selection'])):i for i,x in enumerate(by_value,1)}
    for x in by_prob:x['value_rank']=value_rank[(str(x['api_fixture_id']),str(x['selection']))]
    RANK.write_text(json.dumps({'generated_at_utc':now,'status':'OK','model_version':model_version,'scope':'unique active canonical exposures only','max_probability':by_prob,'best_value':by_value,'policy':{'watch_excluded':True,'stake_changes':False,'r1_r2_deduplicated':True,'r3_conflict_manual':True,'paper_user_execution_is_not_proof_real_bet':True}},ensure_ascii=False,indent=2),encoding='utf-8')

    groups=defaultdict(list)
    for s in settles:groups[s.get('rule') or 'UNKNOWN'].append(s)
    by_rule={}
    for rule,rr in sorted(groups.items()):
        bm=[fnum(x.get('brier_market')) for x in rr];bp=[fnum(x.get('brier_pbk')) for x in rr];lm=[fnum(x.get('logloss_market')) for x in rr];lp=[fnum(x.get('logloss_pbk')) for x in rr]
        bm=[x for x in bm if x is not None];bp=[x for x in bp if x is not None];lm=[x for x in lm if x is not None];lp=[x for x in lp if x is not None]
        by_rule[rule]={'settled_predictions':len(rr),'brier_market':sum(bm)/len(bm) if bm else None,'brier_pbk':sum(bp)/len(bp) if bp else None,'logloss_market':sum(lm)/len(lm) if lm else None,'logloss_pbk':sum(lp)/len(lp) if lp else None,'forward_review_ready':len(rr)>=int(cfg.get('forward_review_min_settled_per_rule',50))}
    PERF.write_text(json.dumps({'generated_at_utc':now,'status':'OK','model_version':model_version,'settled_predictions':len(settles),'by_rule':by_rule,'review_min_settled_per_rule':cfg.get('forward_review_min_settled_per_rule',50),'historical_backfill':'FORBIDDEN'},ensure_ascii=False,indent=2),encoding='utf-8')
    meta={'run_at_utc':now,'status':'OK','model_version':model_version,'predictions':len(preds),'predictions_created':created,'settlements':len(settles),'settlements_created':settled_new,'active_unique_ranked':len(unique),'api_calls':0}
    meta.update(materialize_radar(OPS,forward,preds,cfg,now))
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(meta,ensure_ascii=False))
if __name__=='__main__':main()
