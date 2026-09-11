#!/usr/bin/env python3
"""Stage 53 v3: daily R1/R2/R3 screener and immutable paper-forward log.

Operational source roles
------------------------
API-Football (API_FOOTBALL_KEY):
  * upcoming Big-5 fixtures
  * Bet365 Match Winner price for R1/R2 trigger (when Bet365 is present)
  * all-bookmaker Match Winner odds for executable/best-price snapshot
Football-Data current-season result CSVs:
  * table, last-5 PPG, games remaining, rest days
  * settlement after matches finish

Locked strategy definitions are NOT changed. R1/R2 are evaluated from the first
Bet365 snapshot captured by Stage 53 for each Serie A fixture and that trigger
snapshot is frozen in ops/trigger_ledger.csv.
"""
from __future__ import annotations
import csv, io, json, math, os, re, sys, urllib.parse, urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

SEASON_YEAR = int(os.getenv("API_FOOTBALL_SEASON", "2026"))
FD_SEASON_CODE = os.getenv("FD_SEASON_CODE", "2627")
FD_RESULT_URL = "https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"
API_BASE = "https://v3.football.api-sports.io"

LEAGUES = {
    "E0": {"name":"Premier League","api_league":39,"games_per_team":38},
    "SP1":{"name":"La Liga","api_league":140,"games_per_team":38},
    "I1": {"name":"Serie A","api_league":135,"games_per_team":38},
    "D1": {"name":"Bundesliga","api_league":78,"games_per_team":34},
    "F1": {"name":"Ligue 1","api_league":61,"games_per_team":34},
}

OUT_DIR=Path(os.getenv("OPS_DIR","ops"))
LATEST_SCREEN=OUT_DIR/"latest_screen.csv"
PASSPORTS=OUT_DIR/"context_passports.csv"
FORWARD_LOG=OUT_DIR/"forward_log.csv"
RUN_META=OUT_DIR/"last_run.json"
TRIGGER_LEDGER=OUT_DIR/"trigger_ledger.csv"

FORWARD_FIELDS=[
 "forward_id","rule","screened_at_utc","league","div","api_fixture_id","match_date","kickoff_time",
 "home_team","away_team","bet_market","bet_selection","stake_u","trigger_source","trigger_b365_home",
 "trigger_b365_draw","trigger_b365_away","execution_source","execution_bookmaker","execution_odds",
 "execution_last_update_utc","execution_verified","home_rank","away_rank","home_points","away_points",
 "home_played","away_played","home_remaining","away_remaining","home_last5_ppg","away_last5_ppg",
 "home_rest_days","away_rest_days","status","result","settled_at_utc","profit_u","notes"
]
TRIGGER_FIELDS=["api_fixture_id","captured_at_utc","div","league","match_date","home_team","away_team","b365_home","b365_draw","b365_away","api_update_utc","source"]
SCREEN_FIELDS=[
 "screened_at_utc","div","league","api_fixture_id","match_date","kickoff_time","weekday","home_team","away_team",
 "r1","r2","r3","signal_rules","b365_home","b365_draw","b365_away","unique_away_favorite",
 "home_rank","away_rank","home_points","away_points","home_played","away_played","home_remaining","away_remaining",
 "home_last5_ppg","away_last5_ppg","home_rest_days","away_rest_days","best_home_odds","best_home_book",
 "best_draw_odds","best_draw_book","best_away_odds","best_away_book","execution_odds_source",
 "execution_odds_verified","odds_last_update_utc","passport_status","notes"
]

def http_text(url,headers=None,timeout=30):
    h={"User-Agent":"football-data-bridge/3.0"}; h.update(headers or {})
    req=urllib.request.Request(url,headers=h)
    with urllib.request.urlopen(req,timeout=timeout) as resp: raw=resp.read()
    for enc in ("utf-8-sig","utf-8","latin-1"):
        try:return raw.decode(enc)
        except UnicodeDecodeError:pass
    return raw.decode("latin-1",errors="replace")

def api_get(path,params=None):
    key=os.getenv("API_FOOTBALL_KEY","").strip()
    if not key:return None
    qs=urllib.parse.urlencode(params or {})
    url=API_BASE+path+("?"+qs if qs else "")
    data=json.loads(http_text(url,{"x-apisports-key":key}))
    if data.get("errors"):
        raise RuntimeError(f"API-Football {path}: {data['errors']}")
    return data

def rows_csv(text):return list(csv.DictReader(io.StringIO(text)))
def parse_date(s):
    s=(s or "").strip()
    for fmt in ("%d/%m/%Y","%d/%m/%y","%Y-%m-%d"):
        try:return datetime.strptime(s,fmt).date()
        except ValueError:pass
    return None

def fnum(x):
    try:
        v=float(str(x).strip()); return v if math.isfinite(v) else None
    except:return None

def fmt(x,n=2):return "" if x is None else f"{x:.{n}f}"
def norm(s):
    s=(s or "").lower().replace("&"," and ")
    repl={"internazionale":"inter","inter milan":"inter","man utd":"manchester united","man city":"manchester city",
          "paris sg":"paris saint germain","psg":"paris saint germain","ath madrid":"atletico madrid",
          "ac milan":"milan","nott'm forest":"nottingham forest","wolves":"wolverhampton wanderers"}
    s=repl.get(s.strip(),s)
    s=re.sub(r"\b(fc|cf|afc|calcio|football club|club de futbol)\b"," ",s)
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s).strip())
def sim(a,b):return SequenceMatcher(None,norm(a),norm(b)).ratio()

@dataclass
class TeamState:
    played:int=0; points:int=0; gf:int=0; ga:int=0; last5:deque=None; last_date:object=None
    def __post_init__(self):
        if self.last5 is None:self.last5=deque(maxlen=5)
    @property
    def ppg5(self):return sum(self.last5)/len(self.last5) if self.last5 else None

def completed(r):return (r.get("FTR") or "") in {"H","D","A"} and fnum(r.get("FTHG")) is not None and fnum(r.get("FTAG")) is not None

def build_state(results,cutoff):
    teams=defaultdict(TeamState)
    for r in sorted(results,key=lambda x:parse_date(x.get("Date")) or cutoff):
        d=parse_date(r.get("Date"))
        if not d or d>=cutoff or not completed(r):continue
        h,a=r.get("HomeTeam","").strip(),r.get("AwayTeam","").strip(); hg=int(float(r["FTHG"])); ag=int(float(r["FTAG"])); ftr=r["FTR"]
        hp=3 if ftr=="H" else 1 if ftr=="D" else 0; ap=3 if ftr=="A" else 1 if ftr=="D" else 0
        for t,gf,ga,p in ((h,hg,ag,hp),(a,ag,hg,ap)):
            st=teams[t]; st.played+=1; st.points+=p; st.gf+=gf; st.ga+=ga; st.last5.append(p); st.last_date=d
    table=sorted(teams.items(),key=lambda kv:(kv[1].points,kv[1].gf-kv[1].ga,kv[1].gf),reverse=True)
    return teams,{t:i+1 for i,(t,_) in enumerate(table)}
def match_name(name,cands):
    if name in cands:return name
    scores=[(sim(name,c),c) for c in cands]
    if not scores:return None
    s,c=max(scores); return c if s>=0.70 else None

def find_ref_id(path,search):
    d=api_get(path,{"search":search})
    if not d:return None
    resp=d.get("response",[])
    if not resp:return None
    exact=[x for x in resp if search.lower() in str(x.get("name","")).lower()]
    return (exact[0] if exact else resp[0]).get("id")

def api_fixtures_next():
    out=[]
    for div,info in LEAGUES.items():
        d=api_get("/fixtures",{"league":info["api_league"],"season":SEASON_YEAR,"next":20,"timezone":"UTC"})
        if not d:continue
        for x in d.get("response",[]):
            x["_div"]=div; out.append(x)
    return out

def unpack_matchwinner(api_response,home,away):
    prices=[]
    for item in api_response.get("response",[]):
        update=item.get("update","") or ""
        for bm in item.get("bookmakers",[]):
            bname=bm.get("name","")
            for bet in bm.get("bets",[]):
                name=str(bet.get("name","")).lower()
                if "match winner" not in name and "1x2" not in name and "winner"!=name:continue
                for v in bet.get("values",[]):
                    label=str(v.get("value","")).strip(); odd=fnum(v.get("odd"))
                    if not odd:continue
                    if label.lower() in {"draw","x"}:sel="draw"
                    elif sim(label,home)>=0.70 or label.lower() in {"home","1"}:sel="home"
                    elif sim(label,away)>=0.70 or label.lower() in {"away","2"}:sel="away"
                    else:continue
                    prices.append((sel,odd,bname,update))
    return prices

def get_bet365_prices(fixture_id,bookmaker_id,bet_id,home,away):
    if not bookmaker_id or not bet_id:return {}
    d=api_get("/odds",{"fixture":fixture_id,"bookmaker":bookmaker_id,"bet":bet_id})
    if not d:return {}
    out={}
    for sel,odd,bm,upd in unpack_matchwinner(d,home,away):out[sel]=(odd,bm,upd)
    return out

def get_best_prices(fixture_id,bet_id,home,away):
    d=api_get("/odds",{"fixture":fixture_id,"bet":bet_id})
    if not d:return {}
    best={}
    for sel,odd,bm,upd in unpack_matchwinner(d,home,away):
        if sel not in best or odd>best[sel][0]:best[sel]=(odd,bm,upd)
    return best

def write_dicts(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
def read_trigger_ledger():
    if not TRIGGER_LEDGER.exists():return []
    with TRIGGER_LEDGER.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def read_forward():
    if not FORWARD_LOG.exists():return []
    with FORWARD_LOG.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def settle(log,results_by_div,now):
    for row in log:
        if row.get("status") not in {"PAPER","OPEN"}:continue
        d0=parse_date(row.get("match_date")); hit=None
        for m in results_by_div.get(row.get("div"),[]):
            if not completed(m):continue
            md=parse_date(m.get("Date"))
            if d0 and md and abs((md-d0).days)>1:continue
            if sim(row.get("home_team",""),m.get("HomeTeam",""))>=.84 and sim(row.get("away_team",""),m.get("AwayTeam",""))>=.84:
                hit=m;break
        if not hit:continue
        ftr=hit["FTR"]; row["result"]=ftr; row["settled_at_utc"]=now; row["status"]="SETTLED"
        odds=fnum(row.get("execution_odds")); stake=fnum(row.get("stake_u")) or 1.; sel=row.get("bet_selection")
        won=(sel=="Away" and ftr=="A") or (sel=="Draw" and ftr=="D")
        row["profit_u"]=fmt(stake*(odds-1) if won else -stake,3) if odds else ""

def main():
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"); OUT_DIR.mkdir(parents=True,exist_ok=True)
    key=os.getenv("API_FOOTBALL_KEY","").strip()
    if not key:
        write_dicts(LATEST_SCREEN,SCREEN_FIELDS,[]); write_dicts(PASSPORTS,SCREEN_FIELDS,[])
        RUN_META.write_text(json.dumps({"screened_at_utc":now,"status":"WAITING_FOR_API_FOOTBALL_KEY","fixtures_seen":0,"signal_matches":0},indent=2),encoding="utf-8")
        print("WAITING_FOR_API_FOOTBALL_KEY"); return

    results_by_div={}
    for div in LEAGUES:
        try:results_by_div[div]=rows_csv(http_text(FD_RESULT_URL.format(season=FD_SEASON_CODE,div=div)))
        except Exception as e:print("WARN Football-Data",div,e,file=sys.stderr);results_by_div[div]=[]

    bookmaker_id=find_ref_id("/odds/bookmakers","Bet365")
    bet_id=find_ref_id("/odds/bets","Match Winner")
    fixtures=api_fixtures_next(); screen=[]; passports=[]; signals=[]; best_cache={}
    trigger_rows=read_trigger_ledger(); trigger_by_fixture={str(r.get("api_fixture_id")):r for r in trigger_rows}

    for x in fixtures:
        div=x["_div"]; info=LEAGUES[div]; fx=x.get("fixture",{}); teamsx=x.get("teams",{})
        fixture_id=fx.get("id"); home=teamsx.get("home",{}).get("name",""); away=teamsx.get("away",{}).get("name","")
        try:dt=datetime.fromisoformat(str(fx.get("date","")).replace("Z","+00:00")); d=dt.date(); kickoff=dt.strftime("%H:%M")
        except Exception:continue
        states,ranks=build_state(results_by_div[div],d); hm=match_name(home,states.keys()) or home; am=match_name(away,states.keys()) or away
        hs=states.get(hm,TeamState()); as_=states.get(am,TeamState()); remh=max(info["games_per_team"]-hs.played,0); rema=max(info["games_per_team"]-as_.played,0)
        if div=="I1" and str(fixture_id) not in trigger_by_fixture:
            try:
                fresh=get_bet365_prices(fixture_id,bookmaker_id,bet_id,home,away)
                fh=fresh.get("home",(None,"","") )[0]; fd=fresh.get("draw",(None,"","") )[0]; fa=fresh.get("away",(None,"","") )[0]
                if fh and fd and fa:
                    upd=max([fresh.get(k,(None,"","") )[2] for k in ("home","draw","away")])
                    tr={"api_fixture_id":fixture_id,"captured_at_utc":now,"div":div,"league":info["name"],"match_date":d.isoformat(),
                        "home_team":home,"away_team":away,"b365_home":fh,"b365_draw":fd,"b365_away":fa,"api_update_utc":upd,
                        "source":"API-Football Bet365 first captured by Stage53"}
                    trigger_rows.append(tr); trigger_by_fixture[str(fixture_id)]=tr
            except Exception as e:print("WARN Bet365 odds",fixture_id,e,file=sys.stderr)
        locked=trigger_by_fixture.get(str(fixture_id),{}) if div=="I1" else {}
        bh=fnum(locked.get("b365_home")); bd=fnum(locked.get("b365_draw")); ba=fnum(locked.get("b365_away"))
        away_unique=bool(bh and bd and ba and ba<bh and ba<bd)
        r1=bool(div=="I1" and away_unique and 1.20<=ba<2.10)
        ready5=hs.played>=5 and as_.played>=5 and hs.ppg5 is not None and as_.ppg5 is not None
        r2=bool(r1 and ready5 and as_.ppg5>hs.ppg5)
        wd=d.strftime("%A"); r3=bool(wd=="Monday" and remh<=10 and rema<=10)
        is_signal=r1 or r2 or r3
        best={}; exec_source=""; verified="NO"; last=""
        if is_signal:
            try:
                if fixture_id not in best_cache:best_cache[fixture_id]=get_best_prices(fixture_id,bet_id,home,away)
                best=best_cache[fixture_id]; exec_source="API-Football all-bookmaker Match Winner"; verified="YES" if best else "NO"
                last=max([v[2] for v in best.values()] or [""])
            except Exception as e:print("WARN execution odds",fixture_id,e,file=sys.stderr)
        def bp(sel):return best.get(sel,(None,"","") )
        notes=[]
        if div=="I1" and not bookmaker_id:notes.append("Bet365 not found in API-Football bookmaker catalog; R1/R2 trigger unavailable")
        if div=="I1" and bookmaker_id and not (bh and bd and ba):notes.append("Bet365 Match Winner odds not available yet")
        row={
          "screened_at_utc":now,"div":div,"league":info["name"],"api_fixture_id":fixture_id,"match_date":d.isoformat(),"kickoff_time":kickoff,"weekday":wd,
          "home_team":home,"away_team":away,"r1":"YES" if r1 else "NO","r2":"YES" if r2 else "NO","r3":"YES" if r3 else "NO",
          "signal_rules":"|".join([q for q,v in (("R1",r1),("R2",r2),("R3",r3)) if v]),"b365_home":bh or "","b365_draw":bd or "","b365_away":ba or "",
          "unique_away_favorite":"YES" if away_unique else "NO","home_rank":ranks.get(hm,""),"away_rank":ranks.get(am,""),"home_points":hs.points,"away_points":as_.points,
          "home_played":hs.played,"away_played":as_.played,"home_remaining":remh,"away_remaining":rema,"home_last5_ppg":fmt(hs.ppg5),"away_last5_ppg":fmt(as_.ppg5),
          "home_rest_days":((d-hs.last_date).days if hs.last_date else ""),"away_rest_days":((d-as_.last_date).days if as_.last_date else ""),
          "best_home_odds":bp("home")[0] or "","best_home_book":bp("home")[1],"best_draw_odds":bp("draw")[0] or "","best_draw_book":bp("draw")[1],
          "best_away_odds":bp("away")[0] or "","best_away_book":bp("away")[1],"execution_odds_source":exec_source,"execution_odds_verified":verified,
          "odds_last_update_utc":last,"passport_status":"SIGNAL" if is_signal else "NO SIGNAL","notes":"; ".join(notes)
        }
        screen.append(row)
        if not is_signal:continue
        passports.append(dict(row))
        for rule,flag,sel,keysel in (("R1",r1,"Away","away"),("R2",r2,"Away","away"),("R3",r3,"Draw","draw")):
            if not flag:continue
            eo,eb,eu=bp(keysel); fid=f"{rule}|{div}|{fixture_id}"
            signals.append({
              "forward_id":fid,"rule":rule,"screened_at_utc":now,"league":info["name"],"div":div,"api_fixture_id":fixture_id,"match_date":d.isoformat(),"kickoff_time":kickoff,
              "home_team":home,"away_team":away,"bet_market":"1X2","bet_selection":sel,"stake_u":"1.000","trigger_source":"Stage53 immutable first-captured Bet365 via API-Football",
              "trigger_b365_home":bh or "","trigger_b365_draw":bd or "","trigger_b365_away":ba or "","execution_source":exec_source,"execution_bookmaker":eb,
              "execution_odds":eo or "","execution_last_update_utc":eu,"execution_verified":"YES" if eo else "NO","home_rank":ranks.get(hm,""),"away_rank":ranks.get(am,""),
              "home_points":hs.points,"away_points":as_.points,"home_played":hs.played,"away_played":as_.played,"home_remaining":remh,"away_remaining":rema,
              "home_last5_ppg":fmt(hs.ppg5),"away_last5_ppg":fmt(as_.ppg5),"home_rest_days":((d-hs.last_date).days if hs.last_date else ""),
              "away_rest_days":((d-as_.last_date).days if as_.last_date else ""),"status":"PAPER","result":"","settled_at_utc":"","profit_u":"",
              "notes":"auto-screened; trigger snapshot immutable"
            })

    write_dicts(TRIGGER_LEDGER,TRIGGER_FIELDS,trigger_rows)
    write_dicts(LATEST_SCREEN,SCREEN_FIELDS,screen); write_dicts(PASSPORTS,SCREEN_FIELDS,passports)
    log=read_forward(); existing={r.get("forward_id") for r in log}; added=0
    for s in signals:
        if s["forward_id"] not in existing:log.append(s);existing.add(s["forward_id"]);added+=1
    settle(log,results_by_div,now); write_dicts(FORWARD_LOG,FORWARD_FIELDS,log)
    RUN_META.write_text(json.dumps({"screened_at_utc":now,"status":"OK","season":SEASON_YEAR,"fixtures_seen":len(screen),"signal_matches":len(passports),
                                    "new_forward_rows":added,"trigger_ledger_rows":len(trigger_rows),"bookmaker_bet365_id":bookmaker_id,"match_winner_bet_id":bet_id},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"fixtures":len(screen),"signals":len(passports),"new_forward":added,"forward_rows":len(log)},ensure_ascii=False))

if __name__=="__main__":main()
