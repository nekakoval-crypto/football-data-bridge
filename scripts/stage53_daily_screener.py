#!/usr/bin/env python3
"""Stage 53: daily R1/R2/R3 screener + immutable paper-forward log.

Data roles:
- Football-Data upcoming fixtures/B365 snapshot: RULE TRIGGER source for R1/R2.
- Football-Data current-season results: form/table/remaining/rest and settlement.
- The Odds API (optional ODDS_API_KEY): current EXECUTION-price overlay.

No historical rule is mutated here.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

FD_FIXTURES_URL = "https://www.football-data.co.uk/matches/resources/fixtures.csv"
SEASON_CODE = os.getenv("FD_SEASON_CODE", "2627")
FD_RESULT_URL = "https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"

LEAGUES = {
    "E0": {"name": "Premier League", "games_per_team": 38},
    "SP1": {"name": "La Liga", "games_per_team": 38},
    "I1": {"name": "Serie A", "games_per_team": 38},
    "D1": {"name": "Bundesliga", "games_per_team": 34},
    "F1": {"name": "Ligue 1", "games_per_team": 34},
}

OUT_DIR = Path(os.getenv("OPS_DIR", "ops"))
LATEST_SCREEN = OUT_DIR / "latest_screen.csv"
PASSPORTS = OUT_DIR / "context_passports.csv"
FORWARD_LOG = OUT_DIR / "forward_log.csv"
RUN_META = OUT_DIR / "last_run.json"

FORWARD_FIELDS = [
    "forward_id", "rule", "screened_at_utc", "league", "div", "match_date", "kickoff_time",
    "home_team", "away_team", "bet_market", "bet_selection", "stake_u",
    "trigger_source", "trigger_b365_home", "trigger_b365_draw", "trigger_b365_away",
    "execution_source", "execution_bookmaker", "execution_odds", "execution_last_update_utc",
    "execution_verified", "home_rank", "away_rank", "home_points", "away_points",
    "home_played", "away_played", "home_remaining", "away_remaining",
    "home_last5_ppg", "away_last5_ppg", "home_rest_days", "away_rest_days",
    "status", "result", "settled_at_utc", "profit_u", "notes",
]

SCREEN_FIELDS = [
    "screened_at_utc", "div", "league", "match_date", "kickoff_time", "weekday",
    "home_team", "away_team", "r1", "r2", "r3", "signal_rules",
    "b365_home", "b365_draw", "b365_away", "unique_away_favorite",
    "home_rank", "away_rank", "home_points", "away_points", "home_played", "away_played",
    "home_remaining", "away_remaining", "home_last5_ppg", "away_last5_ppg",
    "home_rest_days", "away_rest_days", "best_home_odds", "best_home_book",
    "best_draw_odds", "best_draw_book", "best_away_odds", "best_away_book",
    "execution_odds_source", "execution_odds_verified", "odds_last_update_utc",
    "passport_status", "notes",
]


def http_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "football-data-bridge/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace")


def parse_csv_text(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def parse_date(s: str):
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def fnum(x):
    try:
        v = float(str(x).strip())
        return v if math.isfinite(v) else None
    except Exception:
        return None


def fmt_num(x, nd=3):
    if x is None:
        return ""
    return f"{x:.{nd}f}"


def normalize_team(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\b(fc|cf|afc|calcio|football club|club de futbol|1908|04|05|1899)\b", " ", s)
    repl = {
        "internazionale": "inter", "inter milan": "inter", "man utd": "manchester united",
        "man city": "manchester city", "psg": "paris saint germain", "paris sg": "paris saint germain",
        "ath madrid": "atletico madrid", "athletic club": "athletic bilbao", "ac milan": "milan",
        "bayern munich": "bayern munchen", "borussia monchengladbach": "monchengladbach",
        "nott'm forest": "nottingham forest", "wolves": "wolverhampton wanderers",
    }
    s = repl.get(s.strip(), s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"\s+", " ", s)


def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_team(a), normalize_team(b)).ratio()


@dataclass
class TeamState:
    played: int = 0
    points: int = 0
    gf: int = 0
    ga: int = 0
    last5_points: deque = None
    last_match_date: object = None

    def __post_init__(self):
        if self.last5_points is None:
            self.last5_points = deque(maxlen=5)

    @property
    def last5_ppg(self):
        return (sum(self.last5_points) / len(self.last5_points)) if self.last5_points else None


def completed_match(row: dict) -> bool:
    return (row.get("FTR") or "").strip() in {"H", "D", "A"} and fnum(row.get("FTHG")) is not None and fnum(row.get("FTAG")) is not None


def build_league_state(results: list[dict], cutoff_date):
    teams = defaultdict(TeamState)
    for row in sorted(results, key=lambda x: parse_date(x.get("Date")) or cutoff_date):
        d = parse_date(row.get("Date"))
        if not d or d >= cutoff_date or not completed_match(row):
            continue
        h, a = row.get("HomeTeam", "").strip(), row.get("AwayTeam", "").strip()
        hg, ag = int(float(row["FTHG"])), int(float(row["FTAG"]))
        ftr = row["FTR"].strip()
        hp = 3 if ftr == "H" else 1 if ftr == "D" else 0
        ap = 3 if ftr == "A" else 1 if ftr == "D" else 0
        for team, gf, ga, pts in ((h, hg, ag, hp), (a, ag, hg, ap)):
            st = teams[team]
            st.played += 1; st.points += pts; st.gf += gf; st.ga += ga
            st.last5_points.append(pts); st.last_match_date = d
    table = sorted(teams.items(), key=lambda kv: (kv[1].points, kv[1].gf-kv[1].ga, kv[1].gf), reverse=True)
    ranks = {team: i+1 for i, (team, _) in enumerate(table)}
    return teams, ranks


def match_team_name(name: str, candidates) -> str | None:
    if name in candidates:
        return name
    best = None; score = 0.0
    for c in candidates:
        s = sim(name, c)
        if s > score:
            best, score = c, s
    return best if score >= 0.72 else None


def get_current_odds_api() -> list[dict]:
    key = os.getenv("ODDS_API_KEY", "").strip()
    if not key:
        return []
    sports_url = "https://api.the-odds-api.com/v4/sports/?apiKey=" + urllib.parse.quote(key)
    sports = json.loads(http_text(sports_url))
    targets = {
        "E0": ["premier league", "epl"],
        "SP1": ["la liga"],
        "I1": ["serie a"],
        "D1": ["bundesliga"],
        "F1": ["ligue 1", "ligue one"],
    }
    sport_key_by_div = {}
    for div, needles in targets.items():
        best = None
        for s in sports:
            hay = (str(s.get("title", "")) + " " + str(s.get("description", "")) + " " + str(s.get("key", ""))).lower()
            if s.get("active") and any(n in hay for n in needles):
                best = s.get("key"); break
        if best:
            sport_key_by_div[div] = best
    out=[]
    for div, sport_key in sport_key_by_div.items():
        params = urllib.parse.urlencode({
            "apiKey": key, "regions": "eu", "markets": "h2h", "oddsFormat": "decimal", "dateFormat": "iso"
        })
        url=f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?{params}"
        try:
            events=json.loads(http_text(url))
        except Exception as e:
            print(f"WARN odds api {div}: {e}", file=sys.stderr); continue
        for ev in events:
            ev["_div"] = div
            out.append(ev)
    return out


def best_prices_for_fixture(fx: dict, api_events: list[dict]):
    h, a = fx["HomeTeam"], fx["AwayTeam"]
    d = parse_date(fx.get("Date"))
    best_event=None; best_score=-1
    for ev in api_events:
        if ev.get("_div") != fx.get("Div"):
            continue
        try:
            evd=datetime.fromisoformat(ev.get("commence_time", "").replace("Z", "+00:00")).date()
        except Exception:
            evd=None
        date_bonus = 0.15 if d and evd and abs((evd-d).days) <= 1 else -0.2
        score=(sim(h,ev.get("home_team",""))+sim(a,ev.get("away_team","")))/2 + date_bonus
        if score > best_score:
            best_event, best_score = ev, score
    if not best_event or best_score < 0.72:
        return None
    best={"home":(None,""),"draw":(None,""),"away":(None,"")}; last=""
    for bm in best_event.get("bookmakers",[]):
        title=bm.get("title",bm.get("key","")); last=max(last,bm.get("last_update","") or "")
        for market in bm.get("markets",[]):
            if market.get("key")!="h2h": continue
            for o in market.get("outcomes",[]):
                name=o.get("name",""); price=fnum(o.get("price"))
                if not price: continue
                if name.lower()=="draw": sel="draw"
                elif sim(name,h)>=0.75: sel="home"
                elif sim(name,a)>=0.75: sel="away"
                else: continue
                if best[sel][0] is None or price>best[sel][0]: best[sel]=(price,title)
    return {"event":best_event,"score":best_score,"best":best,"last":last}


def write_dicts(path: Path, fields, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def read_existing_forward():
    if not FORWARD_LOG.exists(): return []
    with FORWARD_LOG.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def settle_forward(log_rows, results_by_div, now_iso):
    for row in log_rows:
        if row.get("status") not in {"OPEN", "PAPER"}: continue
        div=row.get("div"); target_date=parse_date(row.get("match_date"))
        candidates=results_by_div.get(div,[])
        hit=None
        for m in candidates:
            if not completed_match(m): continue
            md=parse_date(m.get("Date"))
            if target_date and md and abs((md-target_date).days)>1: continue
            if sim(row.get("home_team",""),m.get("HomeTeam",""))>=0.85 and sim(row.get("away_team",""),m.get("AwayTeam",""))>=0.85:
                hit=m; break
        if not hit: continue
        ftr=hit.get("FTR","")
        row["result"]=ftr; row["settled_at_utc"]=now_iso; row["status"]="SETTLED"
        odds=fnum(row.get("execution_odds")); stake=fnum(row.get("stake_u")) or 1.0
        sel=row.get("bet_selection")
        won=(sel=="Away" and ftr=="A") or (sel=="Draw" and ftr=="D")
        if odds:
            row["profit_u"]=fmt_num(stake*(odds-1) if won else -stake,3)
        else:
            row["profit_u"]=""
            row["notes"]=(row.get("notes","")+"; settlement missing verified execution odds").strip("; ")


def main():
    now=datetime.now(timezone.utc); now_iso=now.replace(microsecond=0).isoformat().replace("+00:00","Z")
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    fixtures=parse_csv_text(http_text(FD_FIXTURES_URL))
    fixtures=[r for r in fixtures if r.get("Div") in LEAGUES]
    results_by_div={}
    for div in LEAGUES:
        try:
            results_by_div[div]=parse_csv_text(http_text(FD_RESULT_URL.format(season=SEASON_CODE,div=div)))
        except Exception as e:
            print(f"WARN results {div}: {e}",file=sys.stderr); results_by_div[div]=[]
    api_events=get_current_odds_api()

    screen=[]; passports=[]; signals=[]
    for fx in fixtures:
        div=fx.get("Div"); d=parse_date(fx.get("Date"))
        if not d: continue
        info=LEAGUES[div]; results=results_by_div[div]
        states,ranks=build_league_state(results,d)
        h0,a0=fx.get("HomeTeam","").strip(),fx.get("AwayTeam","").strip()
        h=match_team_name(h0,states.keys()) or h0; a=match_team_name(a0,states.keys()) or a0
        hs=states.get(h,TeamState()); as_=states.get(a,TeamState())
        remh=max(info["games_per_team"]-hs.played,0); rema=max(info["games_per_team"]-as_.played,0)
        bh,bd,ba=fnum(fx.get("B365H")),fnum(fx.get("B365D")),fnum(fx.get("B365A"))
        away_unique=bool(bh and bd and ba and ba<bh and ba<bd)
        r1=bool(div=="I1" and away_unique and 1.20<=ba<2.10)
        ready5=hs.played>=5 and as_.played>=5 and hs.last5_ppg is not None and as_.last5_ppg is not None
        r2=bool(r1 and ready5 and as_.last5_ppg>hs.last5_ppg)
        wd=d.strftime("%A")
        r3=bool(div in LEAGUES and wd=="Monday" and remh<=10 and rema<=10)
        odds_overlay=best_prices_for_fixture(fx,api_events) if api_events else None
        best_home=(None,""); best_draw=(None,""); best_away=(None,""); last=""
        if odds_overlay:
            best_home=odds_overlay["best"]["home"]; best_draw=odds_overlay["best"]["draw"]; best_away=odds_overlay["best"]["away"]; last=odds_overlay["last"]
            exec_source="The Odds API / EU best price"; verified="YES"
        else:
            best_home=(bh,"Football-Data B365 snapshot" if bh else "")
            best_draw=(bd,"Football-Data B365 snapshot" if bd else "")
            best_away=(ba,"Football-Data B365 snapshot" if ba else "")
            exec_source="Football-Data fixture snapshot (fallback, not real-time)"; verified="NO"
        notes=[]
        if not bh or not bd or not ba: notes.append("B365 trigger snapshot incomplete")
        if not api_events: notes.append("ODDS_API_KEY not configured; execution price not live-verified")
        row={
            "screened_at_utc":now_iso,"div":div,"league":info["name"],"match_date":d.isoformat(),"kickoff_time":fx.get("Time","") or "",
            "weekday":wd,"home_team":h0,"away_team":a0,"r1":"YES" if r1 else "NO","r2":"YES" if r2 else "NO","r3":"YES" if r3 else "NO",
            "signal_rules":"|".join([x for x,v in (("R1",r1),("R2",r2),("R3",r3)) if v]),
            "b365_home":bh or "","b365_draw":bd or "","b365_away":ba or "","unique_away_favorite":"YES" if away_unique else "NO",
            "home_rank":ranks.get(h,""),"away_rank":ranks.get(a,""),"home_points":hs.points,"away_points":as_.points,"home_played":hs.played,"away_played":as_.played,
            "home_remaining":remh,"away_remaining":rema,"home_last5_ppg":fmt_num(hs.last5_ppg,2),"away_last5_ppg":fmt_num(as_.last5_ppg,2),
            "home_rest_days":((d-hs.last_match_date).days if hs.last_match_date else ""),"away_rest_days":((d-as_.last_match_date).days if as_.last_match_date else ""),
            "best_home_odds":best_home[0] or "","best_home_book":best_home[1],"best_draw_odds":best_draw[0] or "","best_draw_book":best_draw[1],
            "best_away_odds":best_away[0] or "","best_away_book":best_away[1],"execution_odds_source":exec_source,"execution_odds_verified":verified,
            "odds_last_update_utc":last,"passport_status":"SIGNAL" if (r1 or r2 or r3) else "NO SIGNAL","notes":"; ".join(notes),
        }
        screen.append(row)
        if r1 or r2 or r3:
            passports.append(dict(row))
            for rule,flag,selection,odds_pair in (("R1",r1,"Away",best_away),("R2",r2,"Away",best_away),("R3",r3,"Draw",best_draw)):
                if not flag: continue
                forward_id=f"{rule}|{div}|{d.isoformat()}|{normalize_team(h0)}|{normalize_team(a0)}"
                signals.append({
                    "forward_id":forward_id,"rule":rule,"screened_at_utc":now_iso,"league":info["name"],"div":div,"match_date":d.isoformat(),"kickoff_time":fx.get("Time","") or "",
                    "home_team":h0,"away_team":a0,"bet_market":"1X2","bet_selection":selection,"stake_u":"1.000",
                    "trigger_source":"Football-Data B365 fixture snapshot","trigger_b365_home":bh or "","trigger_b365_draw":bd or "","trigger_b365_away":ba or "",
                    "execution_source":exec_source,"execution_bookmaker":odds_pair[1],"execution_odds":odds_pair[0] or "","execution_last_update_utc":last,
                    "execution_verified":verified,"home_rank":ranks.get(h,""),"away_rank":ranks.get(a,""),"home_points":hs.points,"away_points":as_.points,
                    "home_played":hs.played,"away_played":as_.played,"home_remaining":remh,"away_remaining":rema,
                    "home_last5_ppg":fmt_num(hs.last5_ppg,2),"away_last5_ppg":fmt_num(as_.last5_ppg,2),
                    "home_rest_days":((d-hs.last_match_date).days if hs.last_match_date else ""),"away_rest_days":((d-as_.last_match_date).days if as_.last_match_date else ""),
                    "status":"PAPER","result":"","settled_at_utc":"","profit_u":"","notes":"auto-screened; immutable trigger snapshot",
                })

    write_dicts(LATEST_SCREEN,SCREEN_FIELDS,screen)
    write_dicts(PASSPORTS,SCREEN_FIELDS,passports)
    log=read_existing_forward(); existing={r.get("forward_id") for r in log}
    added=0
    for s in signals:
        if s["forward_id"] not in existing:
            log.append(s); existing.add(s["forward_id"]); added += 1
    settle_forward(log,results_by_div,now_iso)
    write_dicts(FORWARD_LOG,FORWARD_FIELDS,log)
    RUN_META.write_text(json.dumps({
        "screened_at_utc":now_iso,"season_code":SEASON_CODE,"fixtures_seen":len(screen),"signal_matches":len(passports),
        "new_rule_rows_added":added,
        "odds_api_configured":bool(os.getenv("ODDS_API_KEY","")),"odds_api_events":len(api_events),
    },ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"fixtures":len(screen),"signals":len(passports),"forward_rows":len(log),"odds_api_events":len(api_events)},ensure_ascii=False))

if __name__=="__main__":
    main()
