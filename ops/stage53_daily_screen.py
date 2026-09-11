#!/usr/bin/env python3
"""Stage 53 daily screening for locked/prospective football rules.

R1 (LOCKED): Serie A away unique B365 1X2 favorite, 1.20 <= B365A < 2.10.
R2 (LOCKED): R1 + both teams have >=5 prior league games + away last5 PPG > home last5 PPG.
R3 (PROSPECTIVE): Big-5 Monday + both teams <=10 league games remaining before kickoff -> Draw.

Discipline:
- Football-Data B365 is the canonical R1/R2 anchor when available.
- Executable odds are separate and optional (The Odds API adapter).
- R2 is a subset of R1; portfolio stake is not doubled.
- R1/R2 vs R3 on the same match => MANUAL REVIEW.
- No historical rows are inserted into the forward log.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import os
import re
import statistics
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

OUT = Path(os.environ.get("STAGE53_OUT", "stage53_output"))
OUT.mkdir(parents=True, exist_ok=True)

LEAGUES = {
    "E0": {"name": "Premier League", "total_games": 38, "odds_api_tokens": ["epl", "premier league"]},
    "SP1": {"name": "La Liga", "total_games": 38, "odds_api_tokens": ["la liga", "spain"]},
    "I1": {"name": "Serie A", "total_games": 38, "odds_api_tokens": ["serie a", "italy"]},
    "D1": {"name": "Bundesliga", "total_games": 34, "odds_api_tokens": ["bundesliga", "germany"]},
    "F1": {"name": "Ligue 1", "total_games": 34, "odds_api_tokens": ["ligue 1", "france"]},
}


def season_code(today: dt.date) -> str:
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def get_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 stage53-forward-screen"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8-sig", errors="replace")


def get_json(url: str, timeout: int = 30):
    return json.loads(get_text(url, timeout=timeout))


def parse_date(s: str) -> dt.date | None:
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_time(s: str) -> dt.time:
    s = (s or "").strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return dt.datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    return dt.time(15, 0)


def fnum(x):
    try:
        v = float(str(x).strip())
        return v if math.isfinite(v) else None
    except Exception:
        return None


def normalize_team(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("manchester united", "man utd").replace("manchester city", "man city")
    s = s.replace("internazionale", "inter").replace("inter milan", "inter")
    s = s.replace("paris saint germain", "psg").replace("paris st germain", "psg")
    s = re.sub(r"\b(fc|cf|afc|calcio|club|football|futbol|deportivo|ss|as)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def points_for(team: str, row: dict) -> int | None:
    result = row.get("FTR")
    if result not in {"H", "D", "A"}:
        return None
    if row.get("HomeTeam") == team:
        return 3 if result == "H" else 1 if result == "D" else 0
    if row.get("AwayTeam") == team:
        return 3 if result == "A" else 1 if result == "D" else 0
    return None


def completed_before(rows: list[dict], team: str, fixture_dt: dt.datetime) -> list[dict]:
    out = []
    for r in rows:
        if r.get("FTR") not in {"H", "D", "A"}:
            continue
        if team not in {r.get("HomeTeam"), r.get("AwayTeam")}:
            continue
        d = parse_date(r.get("Date", ""))
        if d is None:
            continue
        t = parse_time(r.get("Time", ""))
        if dt.datetime.combine(d, t) < fixture_dt:
            out.append(r)
    out.sort(key=lambda r: dt.datetime.combine(parse_date(r["Date"]), parse_time(r.get("Time", ""))))
    return out


def last5_ppg(prior: list[dict], team: str) -> float | None:
    if len(prior) < 5:
        return None
    pts = [points_for(team, r) for r in prior[-5:]]
    if any(p is None for p in pts):
        return None
    return sum(pts) / 5.0


def fetch_football_data(today: dt.date):
    code = season_code(today)
    data = {}
    errors = []
    for div in LEAGUES:
        urls = [
            f"https://www.football-data.co.uk/mmz4281/{code}/{div}.csv",
            f"https://football-data.co.uk/mmz4281/{code}/{div}.csv",
        ]
        text = None
        for url in urls:
            try:
                text = get_text(url)
                if "HomeTeam" in text and "AwayTeam" in text:
                    break
            except Exception as exc:
                errors.append(f"{div} {url}: {type(exc).__name__}: {exc}")
                text = None
        if text:
            data[div] = list(csv.DictReader(io.StringIO(text)))
    return code, data, errors


def football_data_future_rows(div: str, rows: list[dict], now_utc: dt.datetime):
    # Football-Data current-season files sometimes include upcoming priced rows.
    # Keep blank-result rows and any row whose kickoff has not yet passed.
    out = []
    for r in rows:
        d = parse_date(r.get("Date", ""))
        if d is None:
            continue
        t = parse_time(r.get("Time", ""))
        when = dt.datetime.combine(d, t, tzinfo=dt.timezone.utc)
        if r.get("FTR") not in {"H", "D", "A"} or when >= now_utc:
            rr = dict(r)
            rr["_fixture_dt"] = dt.datetime.combine(d, t)
            out.append(rr)
    return out


def discover_odds_api_sports(api_key: str):
    url = "https://api.the-odds-api.com/v4/sports/?" + urllib.parse.urlencode({"apiKey": api_key})
    sports = get_json(url)
    mapping = {}
    for div, meta in LEAGUES.items():
        best = None
        for s in sports:
            if not s.get("active", True):
                continue
            blob = " ".join([str(s.get("key", "")), str(s.get("title", "")), str(s.get("description", ""))]).lower()
            score = sum(tok in blob for tok in meta["odds_api_tokens"])
            if score and (best is None or score > best[0]):
                best = (score, s.get("key"))
        if best:
            mapping[div] = best[1]
    return mapping


def fetch_odds_api_events(api_key: str, sport_key: str):
    params = {
        "apiKey": api_key,
        "regions": "uk,eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    url = f"https://api.the-odds-api.com/v4/sports/{urllib.parse.quote(sport_key)}/odds/?" + urllib.parse.urlencode(params)
    return get_json(url)


def event_prices(event: dict, selection: str):
    prices = []
    for book in event.get("bookmakers", []):
        title = book.get("title") or book.get("key")
        for market in book.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for o in market.get("outcomes", []):
                name = o.get("name")
                if selection == "Draw" and str(name).lower() == "draw":
                    prices.append((float(o["price"]), title, market.get("last_update") or book.get("last_update")))
                elif selection == "Away" and normalize_team(str(name)) == normalize_team(event.get("away_team", "")):
                    prices.append((float(o["price"]), title, market.get("last_update") or book.get("last_update")))
    prices.sort(reverse=True, key=lambda x: x[0])
    return prices


def match_event(home: str, away: str, kickoff_date: dt.date, events: list[dict]):
    hn, an = normalize_team(home), normalize_team(away)
    exact = []
    for e in events:
        eh, ea = normalize_team(e.get("home_team", "")), normalize_team(e.get("away_team", ""))
        try:
            ed = dt.datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).date()
        except Exception:
            ed = None
        if ed and abs((ed - kickoff_date).days) <= 1 and eh == hn and ea == an:
            exact.append(e)
    return exact[0] if exact else None


def main():
    now_utc = dt.datetime.now(dt.timezone.utc)
    today = now_utc.date()
    code, fd, fd_errors = fetch_football_data(today)

    api_key = os.environ.get("THE_ODDS_API_KEY", "").strip()
    odds_map, odds_events, odds_errors = {}, {}, []
    if api_key:
        try:
            odds_map = discover_odds_api_sports(api_key)
            for div, key in odds_map.items():
                try:
                    odds_events[div] = fetch_odds_api_events(api_key, key)
                except Exception as exc:
                    odds_errors.append(f"{div}/{key}: {type(exc).__name__}: {exc}")
        except Exception as exc:
            odds_errors.append(f"sports discovery: {type(exc).__name__}: {exc}")

    candidates = []
    # First screen Football-Data future rows. These are the only rows that can be canonical R1/R2.
    for div, league_rows in fd.items():
        meta = LEAGUES[div]
        futures = football_data_future_rows(div, league_rows, now_utc)
        for r in futures:
            fixture_dt = r["_fixture_dt"]
            home, away = r.get("HomeTeam", ""), r.get("AwayTeam", "")
            hp = completed_before(league_rows, home, fixture_dt)
            ap = completed_before(league_rows, away, fixture_dt)
            h5, a5 = last5_ppg(hp, home), last5_ppg(ap, away)
            hrem = meta["total_games"] - len(hp)
            arem = meta["total_games"] - len(ap)
            bh, bd, ba = fnum(r.get("B365H")), fnum(r.get("B365D")), fnum(r.get("B365A"))
            r1 = div == "I1" and None not in (bh, bd, ba) and ba < bh and ba < bd and 1.20 <= ba < 2.10
            r2 = bool(r1 and h5 is not None and a5 is not None and len(hp) >= 5 and len(ap) >= 5 and a5 > h5)
            r3 = fixture_dt.strftime("%A") == "Monday" and hrem <= 10 and arem <= 10
            if not (r1 or r2 or r3):
                continue
            tags = []
            if r1: tags.append("R1")
            if r2: tags.append("R2")
            if r3: tags.append("R3")
            selection = "Draw" if r3 and not (r1 or r2) else "Away"
            conflict = bool(r3 and (r1 or r2))
            if conflict:
                selection = "MANUAL"
            anchor = ba if (r1 or r2) else bd
            anchor_book = "B365 / Football-Data" if anchor is not None else ""
            candidate = {
                "candidate_id": f"{fixture_dt.date().isoformat()}_{div}_{normalize_team(home)}_{normalize_team(away)}",
                "screened_at_utc": now_utc.isoformat(),
                "kickoff_date": fixture_dt.date().isoformat(),
                "kickoff_time_source": fixture_dt.time().strftime("%H:%M"),
                "league": meta["name"],
                "division": div,
                "home_team": home,
                "away_team": away,
                "R1_flag": int(r1),
                "R2_flag": int(r2),
                "R3_flag": int(r3),
                "strategy_tags": "|".join(tags),
                "market_selection": selection,
                "anchor_bookmaker": anchor_book,
                "anchor_odds": anchor if anchor is not None else "",
                "home_games_remaining": hrem,
                "away_games_remaining": arem,
                "home_prior_matches": len(hp),
                "away_prior_matches": len(ap),
                "home_last5_ppg": "" if h5 is None else round(h5, 3),
                "away_last5_ppg": "" if a5 is None else round(a5, 3),
                "conflict_flag": "R1_R3_CONFLICT" if conflict else "",
                "decision_status": "MANUAL REVIEW" if conflict else "WAITING",
                "portfolio_stake_u": 0 if conflict else 1,
                "best_exec_bookmaker": "",
                "best_exec_odds": "",
                "exec_snapshot_utc": "",
                "odds_book_count": 0,
                "odds_median": "",
                "data_quality": "CANONICAL_ANCHOR" if (r1 or r2) else "R3_SCHEDULE_ONLY",
            }
            candidates.append(candidate)

    # If The Odds API is available, enrich prices and also discover R3 fixtures that Football-Data has not listed yet.
    if api_key:
        known={(c["division"],normalize_team(c["home_team"]),normalize_team(c["away_team"]),c["kickoff_date"]):c for c in candidates}
        for div, events in odds_events.items():
            meta=LEAGUES[div]
            # enrich existing
            for c in [x for x in candidates if x["division"]==div]:
                e=match_event(c["home_team"],c["away_team"],dt.date.fromisoformat(c["kickoff_date"]),events)
                if e and c["market_selection"] in {"Away","Draw"}:
                    prices=event_prices(e,c["market_selection"])
                    if prices:
                        c["best_exec_odds"],c["best_exec_bookmaker"],c["exec_snapshot_utc"]=prices[0]
                        c["odds_book_count"]=len(prices)
                        c["odds_median"]=round(statistics.median(p[0] for p in prices),3)
            # discover prospective R3 from live fixture feed
            for e in events:
                try:
                    ko=dt.datetime.fromisoformat(e["commence_time"].replace("Z","+00:00"))
                except Exception:
                    continue
                if ko <= now_utc or ko.strftime("%A") != "Monday":
                    continue
                home,away=e.get("home_team",""),e.get("away_team","")
                league_rows=fd.get(div,[])
                fixture_dt=ko.replace(tzinfo=None)
                hp=completed_before(league_rows,home,fixture_dt) if league_rows else []
                ap=completed_before(league_rows,away,fixture_dt) if league_rows else []
                hrem=meta["total_games"]-len(hp); arem=meta["total_games"]-len(ap)
                if hrem>10 or arem>10:
                    continue
                key=(div,normalize_team(home),normalize_team(away),ko.date().isoformat())
                if key in known:
                    continue
                prices=event_prices(e,"Draw")
                c={
                    "candidate_id":f"{ko.date().isoformat()}_{div}_{normalize_team(home)}_{normalize_team(away)}",
                    "screened_at_utc":now_utc.isoformat(),"kickoff_date":ko.date().isoformat(),"kickoff_time_source":ko.strftime("%H:%M"),
                    "league":meta["name"],"division":div,"home_team":home,"away_team":away,
                    "R1_flag":0,"R2_flag":0,"R3_flag":1,"strategy_tags":"R3","market_selection":"Draw",
                    "anchor_bookmaker":"","anchor_odds":"","home_games_remaining":hrem,"away_games_remaining":arem,
                    "home_prior_matches":len(hp),"away_prior_matches":len(ap),"home_last5_ppg":"","away_last5_ppg":"",
                    "conflict_flag":"","decision_status":"WAITING","portfolio_stake_u":1,
                    "best_exec_bookmaker":prices[0][1] if prices else "","best_exec_odds":prices[0][0] if prices else "",
                    "exec_snapshot_utc":prices[0][2] if prices else "","odds_book_count":len(prices),
                    "odds_median":round(statistics.median(p[0] for p in prices),3) if prices else "",
                    "data_quality":"LIVE_FIXTURE_R3"
                }
                candidates.append(c); known[key]=c

    fields = [
        "candidate_id","screened_at_utc","kickoff_date","kickoff_time_source","league","division","home_team","away_team",
        "R1_flag","R2_flag","R3_flag","strategy_tags","market_selection","anchor_bookmaker","anchor_odds",
        "best_exec_bookmaker","best_exec_odds","exec_snapshot_utc","odds_book_count","odds_median",
        "home_games_remaining","away_games_remaining","home_prior_matches","away_prior_matches","home_last5_ppg","away_last5_ppg",
        "conflict_flag","decision_status","portfolio_stake_u","data_quality"
    ]
    candidates.sort(key=lambda c:(c["kickoff_date"],c["league"],c["home_team"]))
    with open(OUT/"stage53_candidates.csv","w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(candidates)

    meta={
        "screened_at_utc":now_utc.isoformat(),"season_code":code,"football_data_divisions":sorted(fd),
        "football_data_errors":fd_errors,"the_odds_api_enabled":bool(api_key),"odds_api_sport_mapping":odds_map,
        "odds_api_errors":odds_errors,"candidate_count":len(candidates),
        "R1_count":sum(c["R1_flag"] for c in candidates),"R2_count":sum(c["R2_flag"] for c in candidates),
        "R3_count":sum(c["R3_flag"] for c in candidates),"conflict_count":sum(bool(c["conflict_flag"]) for c in candidates),
    }
    (OUT/"stage53_run_meta.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
