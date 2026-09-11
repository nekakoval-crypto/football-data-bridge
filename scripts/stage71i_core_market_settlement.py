#!/usr/bin/env python3
"""Stage71I — settle prospective raw core-market observations from FT scores.

Research data only. No signal, WATCH or promotion side effects.
"""
from __future__ import annotations
import csv, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import stage53_daily_screener as s53

OPS=Path(os.getenv('OPS_DIR','ops'));OUT=OPS/'stage71i_market_settlements.csv';META=OPS/'stage71i_last_run.json'
SOURCES={
 'TEAM_TOTAL':'stage71c_team_total_closes.csv',
 'DOUBLE_CHANCE':'stage71e_double_chance_closes.csv',
 'EUROPEAN_HANDICAP':'stage71f_eh_closes.csv',
 'DRAW_NO_BET':'stage71g_dnb_closes.csv',
}
FIELDS=['settlement_key','market_family','api_fixture_id','league','league_id','kickoff_utc','settled_at_utc','home_team','away_team','market_key','line','team_side','final_home_goals','final_away_goals','selection_a','selection_b','selection_c','result_a','result_b','result_c','bet365_close_a','bet365_close_b','bet365_close_c','marathon_close_a','marathon_close_b','marathon_close_c','bet365_pnl_a','bet365_pnl_b','bet365_pnl_c','marathon_pnl_a','marathon_pnl_b','marathon_pnl_c','fixture_status','settlement_status','note']

def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def read_csv(path):
 if not path.exists():return []
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_csv(path,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');w.writeheader();w.writerows(rows)
def fnum(v):
 try:
  x=float(str(v).strip());return x if math.isfinite(x) else None
 except:return None
def pnl(result,odd):
 o=fnum(odd)
 if o is None or o<=1:return ''
 if result=='WIN':return f'{o-1:.6f}'
 if result=='LOSS':return '-1.000000'
 if result=='PUSH':return '0.000000'
 return ''
def parse_int(v):
 try:return int(v)
 except:return None
def fixture_result(fid):
 raw=s53.api_get('/fixtures',{'id':fid});resp=(raw or {}).get('response',[])
 if not resp:return None
 x=resp[0];fx=x.get('fixture',{}) or {};status=((fx.get('status') or {}).get('short') or '').upper();score=(x.get('score') or {}).get('fulltime') or {};hg=parse_int(score.get('home'));ag=parse_int(score.get('away'))
 if status=='FT' and (hg is None or ag is None):
  goals=x.get('goals',{}) or {};hg=parse_int(goals.get('home'));ag=parse_int(goals.get('away'))
 return {'status':status,'home':hg,'away':ag}
def result_pair_winloss(win_a,draw_push=False):
 if draw_push:return ('PUSH','PUSH')
 return ('WIN','LOSS') if win_a else ('LOSS','WIN')
def base_row(fam,r,hg,ag,key,line='',team_side=''):
 return {'settlement_key':key,'market_family':fam,'api_fixture_id':r.get('api_fixture_id',''),'league':r.get('league',''),'league_id':r.get('league_id',''),'kickoff_utc':r.get('kickoff_utc',''),'settled_at_utc':now_iso(),'home_team':r.get('home_team',''),'away_team':r.get('away_team',''),'market_key':r.get('market_key',''),'line':line,'team_side':team_side,'final_home_goals':hg,'final_away_goals':ag,'fixture_status':'FT','settlement_status':'SETTLED','note':'Prospective observed-close research settlement; not proof of a placed bet'}
def settle_team_total(r,hg,ag):
 line=fnum(r.get('line'))
 if line is None:return None
 side=str(r.get('team_side') or '').upper();goals=hg if side=='H' else ag if side=='A' else None
 if goals is None:return None
 if goals>line:over,under='WIN','LOSS'
 elif goals<line:over,under='LOSS','WIN'
 else:over=under='PUSH'
 key='TEAM_TOTAL|'+str(r.get('market_key') or f"{r.get('api_fixture_id')}|{side}|{line:g}")
 z=base_row('TEAM_TOTAL',r,hg,ag,key,f'{line:g}',side);z.update({'selection_a':'OVER','selection_b':'UNDER','result_a':over,'result_b':under,'bet365_close_a':r.get('bet365_close_over',''),'bet365_close_b':r.get('bet365_close_under',''),'marathon_close_a':r.get('user_close_over',''),'marathon_close_b':r.get('user_close_under','')});return z
def settle_dc(r,hg,ag):
 draw=hg==ag;home=hg>ag;away=ag>hg
 res=('WIN' if home or draw else 'LOSS','WIN' if away or draw else 'LOSS','WIN' if not draw else 'LOSS');key=f"DOUBLE_CHANCE|{r.get('api_fixture_id')}"
 z=base_row('DOUBLE_CHANCE',r,hg,ag,key);z.update({'selection_a':'1X','selection_b':'X2','selection_c':'12','result_a':res[0],'result_b':res[1],'result_c':res[2],'bet365_close_a':r.get('bet365_close_1x',''),'bet365_close_b':r.get('bet365_close_x2',''),'bet365_close_c':r.get('bet365_close_12',''),'marathon_close_a':r.get('user_close_1x',''),'marathon_close_b':r.get('user_close_x2',''),'marathon_close_c':r.get('user_close_12','')});return z
def settle_dnb(r,hg,ag):
 if hg==ag:a=b='PUSH'
 elif hg>ag:a,b='WIN','LOSS'
 else:a,b='LOSS','WIN'
 key=f"DRAW_NO_BET|{r.get('api_fixture_id')}";z=base_row('DRAW_NO_BET',r,hg,ag,key,'0');z.update({'selection_a':'F1(0)','selection_b':'F2(0)','result_a':a,'result_b':b,'bet365_close_a':r.get('bet365_close_f1_0',''),'bet365_close_b':r.get('bet365_close_f2_0',''),'marathon_close_a':r.get('user_close_f1_0',''),'marathon_close_b':r.get('user_close_f2_0','')});return z
def settle_eh(r,hg,ag):
 line=fnum(r.get('home_handicap_line'))
 if line is None:return None
 adj=hg+line
 if adj>ag:res=('WIN','LOSS','LOSS')
 elif adj<ag:res=('LOSS','LOSS','WIN')
 else:res=('LOSS','WIN','LOSS')
 key='EUROPEAN_HANDICAP|'+str(r.get('market_key') or f"{r.get('api_fixture_id')}|{line:+g}");z=base_row('EUROPEAN_HANDICAP',r,hg,ag,key,f'{line:+g}');z.update({'selection_a':'HOME','selection_b':'DRAW','selection_c':'AWAY','result_a':res[0],'result_b':res[1],'result_c':res[2],'bet365_close_a':r.get('bet365_close_home',''),'bet365_close_b':r.get('bet365_close_draw',''),'bet365_close_c':r.get('bet365_close_away',''),'marathon_close_a':r.get('user_close_home',''),'marathon_close_b':r.get('user_close_draw',''),'marathon_close_c':r.get('user_close_away','')});return z

def finalize(z):
 if not z:return None
 for suffix in ('a','b','c'):
  z[f'bet365_pnl_{suffix}']=pnl(z.get(f'result_{suffix}',''),z.get(f'bet365_close_{suffix}',''))
  z[f'marathon_pnl_{suffix}']=pnl(z.get(f'result_{suffix}',''),z.get(f'marathon_close_{suffix}',''))
 return z

def main():
 existing=read_csv(OUT);keys={r.get('settlement_key','') for r in existing};pending=[]
 for fam,name in SOURCES.items():
  for r in read_csv(OPS/name):
   if str(r.get('status') or '').upper()!='OBSERVED_CLOSE_FROZEN':continue
   if fam=='TEAM_TOTAL':key='TEAM_TOTAL|'+str(r.get('market_key') or '')
   elif fam=='EUROPEAN_HANDICAP':key='EUROPEAN_HANDICAP|'+str(r.get('market_key') or '')
   else:key=f"{fam}|{r.get('api_fixture_id')}"
   if key and key not in keys:pending.append((fam,r,key))
 fids=sorted({str(r.get('api_fixture_id') or '') for _,r,_ in pending if r.get('api_fixture_id')});results={};calls=0;non_ft=[]
 for f in fids:
  try:res=fixture_result(f);calls+=1
  except Exception as e:non_ft.append({'fixture_id':f,'status':'API_ERROR','detail':str(e)});continue
  if not res or res.get('status')!='FT' or res.get('home') is None or res.get('away') is None:
   non_ft.append({'fixture_id':f,'status':None if not res else res.get('status'),'detail':'Not auto-settled; FT regulation score required'});continue
  results[f]=res
 added=0
 for fam,r,key in pending:
  f=str(r.get('api_fixture_id') or '');res=results.get(f)
  if not res:continue
  hg,ag=res['home'],res['away']
  if fam=='TEAM_TOTAL':z=settle_team_total(r,hg,ag)
  elif fam=='DOUBLE_CHANCE':z=settle_dc(r,hg,ag)
  elif fam=='DRAW_NO_BET':z=settle_dnb(r,hg,ag)
  else:z=settle_eh(r,hg,ag)
  z=finalize(z)
  if z and z['settlement_key'] not in keys:existing.append(z);keys.add(z['settlement_key']);added+=1
 write_csv(OUT,existing)
 fam_counts={}
 for r in existing:fam_counts[r.get('market_family','')]=fam_counts.get(r.get('market_family',''),0)+1
 meta={'run_at_utc':now_iso(),'status':'OK','mode':'RESEARCH_SETTLEMENT_ONLY','pending_market_rows':len(pending),'pending_unique_fixtures':len(fids),'fixture_api_calls':calls,'new_settlement_rows':added,'total_settlement_rows':len(existing),'settlement_rows_by_family':fam_counts,'non_ft_or_review_fixtures':non_ft[:100],'signals_created':0,'api_calls':calls};META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
