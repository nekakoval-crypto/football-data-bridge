#!/usr/bin/env python3
"""Stage 71 prospective R1/R2 challenger capture across the locked league scope.

Research-only. It never writes canonical forward files.

- Freezes the first complete Bet365 1X2 snapshot captured for upcoming fixtures.
- Evaluates the exact R1 analogue in non-Serie-A leagues.
- Evaluates the exact R2 analogue only close to kickoff, using completed current-
  season league matches before the fixture.
- Captures Marathonbet away-win price when a research signal is first created.
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

OPS = Path(os.getenv("OPS_DIR", "ops"))
CATALOG = OPS / "stage71_league_catalog.csv"
TRIGGERS = OPS / "stage71_research_trigger_ledger.csv"
FORWARD = OPS / "stage71_challenger_forward.csv"
META = OPS / "stage71_capture_last_run.json"
SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))
NEXT_PER_LEAGUE = int(os.getenv("STAGE71_NEXT_PER_LEAGUE", "5"))
R2_FREEZE_HOURS = float(os.getenv("STAGE71_R2_FREEZE_HOURS", "12"))

TRIGGER_FIELDS = [
    "api_fixture_id","captured_at_utc","country","league","api_league_id","kickoff_utc",
    "home_team_id","home_team","away_team_id","away_team","b365_home","b365_draw","b365_away",
    "api_update_utc","source"
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
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def completed_fixture_rows(api_league_id):
    d=s53.api_get("/fixtures", {"league":api_league_id,"season":SEASON,"status":"FT","timezone":"UTC"})
    return (d or {}).get("response", [])


def next_fixture_rows(api_league_id):
    d=s53.api_get("/fixtures", {"league":api_league_id,"season":SEASON,"next":NEXT_PER_LEAGUE,"timezone":"UTC"})
    return (d or {}).get("response", [])


def points(hg, ag):
    if hg is None or ag is None:return (None,None)
    if hg>ag:return (3,0)
    if hg<ag:return (0,3)
    return (1,1)


def team_state_before(completed, cutoff, home_id, away_id):
    hist=defaultdict(list)
    for x in completed:
        fx=x.get("fixture",{}) or {}; dt=parse_dt(fx.get("date"))
        if not dt or dt>=cutoff: continue
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
    try:
        d=s53.api_get("/odds", {"fixture":fixture_id,"bet":bet_id})
        prices=s53.unpack_matchwinner(d or {}, home, away)
        cand=[(odd,upd) for sel,odd,bm,upd in prices if sel=="away" and str(bm).strip().lower()=="marathonbet"]
        if not cand:return None,""
        # Same response can contain one snapshot per bookmaker; use max only to defend against duplicate values.
        return max(cand, key=lambda z:z[0])
    except Exception:
        return None,""


def settle_rows(rows, completed_by_league, now):
    settled=0
    result_maps={}
    for lid, comp in completed_by_league.items():
        m={}
        for x in comp:
            fx=x.get("fixture",{}) or {}; fid=str(fx.get("id") or "")
            teams=x.get("teams",{}) or {}; goals=x.get("goals",{}) or {}
            m[fid]=(inum(goals.get("home")), inum(goals.get("away")), str((fx.get("status") or {}).get("short") or ""))
        result_maps[str(lid)]=m
    for r in rows:
        if str(r.get("status") or "").upper()!="PENDING":continue
        ko=parse_dt(r.get("kickoff_utc"))
        if not ko or now<=ko:continue
        hit=result_maps.get(str(r.get("api_league_id") or ""),{}).get(str(r.get("api_fixture_id") or ""))
        if not hit:continue
        hg,ag,st=hit
        if st!="FT" or hg is None or ag is None:continue
        won=ag>hg
        r["status"]="SETTLED"; r["result"]="W" if won else "L"
        r["final_home_goals"]=hg; r["final_away_goals"]=ag; r["settled_at_utc"]=iso(now)
        o=fnum(r.get("user_odds"))
        r["user_profit_u"]="" if o is None else f"{(o-1.0 if won else -1.0):.3f}"
        settled+=1
    return settled


def main():
    now=now_dt(); OPS.mkdir(parents=True, exist_ok=True)
    catalog=[r for r in read_csv(CATALOG) if r.get("api_league_id")]
    if not catalog:
        META.write_text(json.dumps({"run_at_utc":iso(now),"status":"WAITING_FOR_STAGE71_CATALOG"},indent=2),encoding="utf-8"); return

    triggers=read_csv(TRIGGERS); trig_by_id={str(r.get("api_fixture_id")):r for r in triggers}
    forward=read_csv(FORWARD); existing_ids={r.get("research_id") for r in forward}
    bookmaker_id=s53.find_ref_id("/odds/bookmakers","Bet365")
    bet_id=s53.find_ref_id("/odds/bets","Match Winner")
    api_calls=2; warnings=[]; new_triggers=0; new_r1=0; new_r2=0; odds_calls=0; marathon_calls=0

    upcoming_by_league={}
    # Serie A is already captured canonically by Stage53; avoid duplicating it here.
    research_catalog=[r for r in catalog if r.get("league")!="Serie A"]
    for lg in research_catalog:
        lid=lg["api_league_id"]
        try:
            upcoming=next_fixture_rows(lid); api_calls+=1; upcoming_by_league[str(lid)]=upcoming
        except Exception as e:
            warnings.append(f"{lg['league']}: fixtures-next error {e}"); upcoming=[]; upcoming_by_league[str(lid)]=[]
        for x in upcoming:
            fx=x.get("fixture",{}) or {}; fid=str(fx.get("id") or "")
            if not fid or fid in trig_by_id:continue
            teams=x.get("teams",{}) or {}; home=(teams.get("home") or {}); away=(teams.get("away") or {})
            try:
                fresh=s53.get_bet365_prices(fid,bookmaker_id,bet_id,home.get("name","") or "",away.get("name","") or "")
                api_calls+=1; odds_calls+=1
                bh=fresh.get("home",(None,"","") )[0]; bd=fresh.get("draw",(None,"","") )[0]; ba=fresh.get("away",(None,"","") )[0]
                if bh and bd and ba:
                    upd=max([fresh.get(k,(None,"","") )[2] for k in ("home","draw","away")])
                    tr={
                        "api_fixture_id":fid,"captured_at_utc":iso(now),"country":lg.get("country") or "","league":lg.get("league") or "",
                        "api_league_id":lid,"kickoff_utc":fx.get("date") or "","home_team_id":home.get("id") or "","home_team":home.get("name") or "",
                        "away_team_id":away.get("id") or "","away_team":away.get("name") or "","b365_home":bh,"b365_draw":bd,"b365_away":ba,
                        "api_update_utc":upd,"source":"Stage71 first complete Bet365 1X2 capture"
                    }
                    triggers.append(tr); trig_by_id[fid]=tr; new_triggers+=1
            except Exception as e:
                warnings.append(f"{lg['league']} fixture {fid}: Bet365 trigger error {e}")

    # Completed-season data is fetched only where a trigger/pending research row needs it.
    need_completed=set()
    now_iso=iso(now)
    for t in triggers:
        ko=parse_dt(t.get("kickoff_utc")); lid=str(t.get("api_league_id") or "")
        if lid and ko and ko>now: need_completed.add(lid)
    for r in forward:
        if r.get("status")=="PENDING": need_completed.add(str(r.get("api_league_id") or ""))

    completed_by_league={}
    for lid in sorted(x for x in need_completed if x):
        try: completed_by_league[lid]=completed_fixture_rows(lid); api_calls+=1
        except Exception as e: warnings.append(f"league {lid}: completed fixtures error {e}"); completed_by_league[lid]=[]

    for t in triggers:
        fid=str(t.get("api_fixture_id") or ""); lid=str(t.get("api_league_id") or ""); ko=parse_dt(t.get("kickoff_utc"))
        if not fid or not lid or not ko or ko<=now:continue
        if not r1_from_trigger(t):continue
        hid=inum(t.get("home_team_id")); aid=inum(t.get("away_team_id"))
        (hp,hppg),(ap,appg)=team_state_before(completed_by_league.get(lid,[]),ko,hid,aid)
        user_odd,user_upd=marathon_away_price(fid,bet_id,t.get("home_team") or "",t.get("away_team") or "")
        api_calls+=1; marathon_calls+=1
        base={
            "country":t.get("country") or "","league":t.get("league") or "","api_league_id":lid,"api_fixture_id":fid,"kickoff_utc":t.get("kickoff_utc") or "",
            "home_team_id":t.get("home_team_id") or "","home_team":t.get("home_team") or "","away_team_id":t.get("away_team_id") or "","away_team":t.get("away_team") or "",
            "selection":"П2","stake_u":"1.000","trigger_captured_at_utc":t.get("captured_at_utc") or "","trigger_b365_home":t.get("b365_home") or "",
            "trigger_b365_draw":t.get("b365_draw") or "","trigger_b365_away":t.get("b365_away") or "","home_played":hp,"away_played":ap,
            "home_last5_ppg":"" if hppg is None else f"{hppg:.3f}","away_last5_ppg":"" if appg is None else f"{appg:.3f}",
            "user_bookmaker":"Marathonbet","user_odds":"" if user_odd is None else user_odd,"user_price_captured_at_utc":iso(now) if user_odd is not None else "",
            "status":"PENDING","result":"","final_home_goals":"","final_away_goals":"","user_profit_u":"","settled_at_utc":"",
        }
        rid=f"R1|{lid}|{fid}"
        if rid not in existing_ids:
            row=dict(base); row.update({"research_id":rid,"family":"R1","eligibility_frozen_at_utc":t.get("captured_at_utc") or "","notes":"research-only exact R1 analogue; never canonical automatically"})
            forward.append(row); existing_ids.add(rid); new_r1+=1

        hrs=(ko-now).total_seconds()/3600.0
        r2_ok=hp>=5 and ap>=5 and hppg is not None and appg is not None and appg>hppg
        rid2=f"R2|{lid}|{fid}"
        if hrs<=R2_FREEZE_HOURS and r2_ok and rid2 not in existing_ids:
            row=dict(base); row.update({"research_id":rid2,"family":"R2","eligibility_frozen_at_utc":iso(now),"notes":"research-only exact R2 analogue frozen close to kickoff; never canonical automatically"})
            forward.append(row); existing_ids.add(rid2); new_r2+=1

    settled=settle_rows(forward, completed_by_league, now)
    write_csv(TRIGGERS, TRIGGER_FIELDS, triggers); write_csv(FORWARD, FORWARD_FIELDS, forward)
    META.write_text(json.dumps({
        "run_at_utc":iso(now),"status":"OK","research_leagues":len(research_catalog),"new_triggers":new_triggers,
        "new_r1_rows":new_r1,"new_r2_rows":new_r2,"settled_rows":settled,"trigger_rows":len(triggers),"forward_rows":len(forward),
        "api_calls":api_calls,"odds_calls":odds_calls,"marathon_calls":marathon_calls,"warnings":warnings
    },ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"new_triggers":new_triggers,"new_r1":new_r1,"new_r2":new_r2,"settled":settled,"api_calls":api_calls,"warnings":len(warnings)},ensure_ascii=False))

if __name__=="__main__":main()
