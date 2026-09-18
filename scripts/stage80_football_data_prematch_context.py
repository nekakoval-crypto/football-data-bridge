#!/usr/bin/env python3
"""Stage80 — no-lookahead historical pre-match context from Football-Data.

Builds deterministic research features from the normalized Top-5 9-season
Football-Data matrix. Every feature for a match is computed only from matches on
strictly earlier calendar dates in the same league-season. Results from the same
calendar date are applied only after all rows on that date have been projected,
so simultaneous/unknown-kickoff matches cannot leak into one another.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

VERSION = "PBK_STAGE80_FOOTBALL_DATA_PREMATCH_CONTEXT_V1"

FIELDS = [
    "historical_match_id","league_code","league_name","country","season_label",
    "date_iso","time_local","weekday_iso","weekday_name","is_monday","is_thursday",
    "is_weekend","kickoff_minutes_local","home_team","away_team",
    "home_rest_days","away_rest_days","rest_advantage_days",
    "home_matches_prev_7d","away_matches_prev_7d",
    "home_matches_prev_14d","away_matches_prev_14d",
    "home_short_rest_le3d","away_short_rest_le3d",
    "home_played_pre","away_played_pre","home_points_pre","away_points_pre",
    "home_ppg_pre","away_ppg_pre","home_gf_pre","home_ga_pre","home_gd_pre",
    "away_gf_pre","away_ga_pre","away_gd_pre","home_rank_pre","away_rank_pre",
    "table_teams_with_history",
    "home_form_matches_last5","away_form_matches_last5",
    "home_points_last5","away_points_last5","home_ppg_last5","away_ppg_last5",
    "home_gf_last5","home_ga_last5","away_gf_last5","away_ga_last5",
    "home_form_matches_last10","away_form_matches_last10",
    "home_points_last10","away_points_last10","home_ppg_last10","away_ppg_last10",
    "home_gf_last10","home_ga_last10","away_gf_last10","away_ga_last10",
    "home_home_matches_last5","away_away_matches_last5",
    "home_home_points_last5","away_away_points_last5",
    "home_home_ppg_last5","away_away_ppg_last5",
    "same_day_results_excluded","no_lookahead","historical_backfill_only",
    "research_only","operational_betting_authority","creates_signal",
    "probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def sval(value):
    return str(value or "").strip()


def as_int(value):
    raw=sval(value)
    if not raw:
        return None
    try:
        return int(float(raw))
    except (TypeError,ValueError):
        return None


def parse_day(value):
    raw=sval(value)
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def parse_time_minutes(value):
    raw=sval(value)
    if not raw:
        return None
    for fmt in ("%H:%M","%H:%M:%S"):
        try:
            dt=datetime.strptime(raw,fmt)
            return dt.hour*60+dt.minute
        except ValueError:
            pass
    return None


def pct_bool(value):
    return "true" if value else "false"


def num(value,digits=3):
    if value is None:
        return ""
    if isinstance(value,int):
        return value
    return round(float(value),digits)


def ppg(points,matches):
    return None if not matches else points/matches


def result_points(result, side):
    if result=="D":
        return 1
    if result=="H":
        return 3 if side=="H" else 0
    if result=="A":
        return 3 if side=="A" else 0
    return None


def load_rows(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    tmp.replace(path)


def write_json(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)


def empty_team_state():
    return {"played":0,"points":0,"gf":0,"ga":0,"history":[]}


def table_ranks(states):
    eligible=[]
    for team,state in states.items():
        if state["played"]<=0:
            continue
        gd=state["gf"]-state["ga"]
        eligible.append((team,state["points"],gd,state["gf"]))
    eligible.sort(key=lambda x:(-x[1],-x[2],-x[3],x[0]))
    return {team:i+1 for i,(team,_,__,___) in enumerate(eligible)},len(eligible)


def previous_matches(history,current_day,days):
    lower=current_day-timedelta(days=days)
    return [
        row for row in history
        if lower <= row["day"] < current_day
    ]


def last_n(history,n,venue=None):
    rows=history if venue is None else [r for r in history if r["venue"]==venue]
    return rows[-n:]


def summarize(rows):
    return {
        "matches":len(rows),
        "points":sum(r["points"] for r in rows),
        "gf":sum(r["gf"] for r in rows),
        "ga":sum(r["ga"] for r in rows),
    }


def rest_days(history,current_day):
    if not history:
        return None
    previous=max(r["day"] for r in history if r["day"] < current_day) if any(r["day"] < current_day for r in history) else None
    return None if previous is None else (current_day-previous).days


def feature_row(row,current_day,states):
    home=sval(row.get("home_team")); away=sval(row.get("away_team"))
    hs=states.setdefault(home,empty_team_state())
    as_=states.setdefault(away,empty_team_state())
    ranks,table_count=table_ranks(states)

    h_rest=rest_days(hs["history"],current_day)
    a_rest=rest_days(as_["history"],current_day)
    rest_adv=None if h_rest is None or a_rest is None else h_rest-a_rest

    h7=len(previous_matches(hs["history"],current_day,7))
    a7=len(previous_matches(as_["history"],current_day,7))
    h14=len(previous_matches(hs["history"],current_day,14))
    a14=len(previous_matches(as_["history"],current_day,14))

    h5=summarize(last_n(hs["history"],5))
    a5=summarize(last_n(as_["history"],5))
    h10=summarize(last_n(hs["history"],10))
    a10=summarize(last_n(as_["history"],10))
    hh5=summarize(last_n(hs["history"],5,"H"))
    aa5=summarize(last_n(as_["history"],5,"A"))

    weekday=current_day.isoweekday()
    minutes=parse_time_minutes(row.get("time_local"))

    return {
        "historical_match_id":sval(row.get("historical_match_id")),
        "league_code":sval(row.get("league_code")),
        "league_name":sval(row.get("league_name")),
        "country":sval(row.get("country")),
        "season_label":sval(row.get("season_label")),
        "date_iso":current_day.isoformat(),
        "time_local":sval(row.get("time_local")),
        "weekday_iso":weekday,
        "weekday_name":current_day.strftime("%A").upper(),
        "is_monday":pct_bool(weekday==1),
        "is_thursday":pct_bool(weekday==4),
        "is_weekend":pct_bool(weekday in {6,7}),
        "kickoff_minutes_local":"" if minutes is None else minutes,
        "home_team":home,"away_team":away,
        "home_rest_days":"" if h_rest is None else h_rest,
        "away_rest_days":"" if a_rest is None else a_rest,
        "rest_advantage_days":"" if rest_adv is None else rest_adv,
        "home_matches_prev_7d":h7,"away_matches_prev_7d":a7,
        "home_matches_prev_14d":h14,"away_matches_prev_14d":a14,
        "home_short_rest_le3d":"" if h_rest is None else pct_bool(h_rest<=3),
        "away_short_rest_le3d":"" if a_rest is None else pct_bool(a_rest<=3),
        "home_played_pre":hs["played"],"away_played_pre":as_["played"],
        "home_points_pre":hs["points"],"away_points_pre":as_["points"],
        "home_ppg_pre":num(ppg(hs["points"],hs["played"])),
        "away_ppg_pre":num(ppg(as_["points"],as_["played"])),
        "home_gf_pre":hs["gf"],"home_ga_pre":hs["ga"],"home_gd_pre":hs["gf"]-hs["ga"],
        "away_gf_pre":as_["gf"],"away_ga_pre":as_["ga"],"away_gd_pre":as_["gf"]-as_["ga"],
        "home_rank_pre":ranks.get(home,""),"away_rank_pre":ranks.get(away,""),
        "table_teams_with_history":table_count,
        "home_form_matches_last5":h5["matches"],"away_form_matches_last5":a5["matches"],
        "home_points_last5":h5["points"],"away_points_last5":a5["points"],
        "home_ppg_last5":num(ppg(h5["points"],h5["matches"])),
        "away_ppg_last5":num(ppg(a5["points"],a5["matches"])),
        "home_gf_last5":h5["gf"],"home_ga_last5":h5["ga"],
        "away_gf_last5":a5["gf"],"away_ga_last5":a5["ga"],
        "home_form_matches_last10":h10["matches"],"away_form_matches_last10":a10["matches"],
        "home_points_last10":h10["points"],"away_points_last10":a10["points"],
        "home_ppg_last10":num(ppg(h10["points"],h10["matches"])),
        "away_ppg_last10":num(ppg(a10["points"],a10["matches"])),
        "home_gf_last10":h10["gf"],"home_ga_last10":h10["ga"],
        "away_gf_last10":a10["gf"],"away_ga_last10":a10["ga"],
        "home_home_matches_last5":hh5["matches"],"away_away_matches_last5":aa5["matches"],
        "home_home_points_last5":hh5["points"],"away_away_points_last5":aa5["points"],
        "home_home_ppg_last5":num(ppg(hh5["points"],hh5["matches"])),
        "away_away_ppg_last5":num(ppg(aa5["points"],aa5["matches"])),
        "same_day_results_excluded":"true","no_lookahead":"true",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
    }


def apply_result(row,current_day,states):
    home=sval(row.get("home_team")); away=sval(row.get("away_team"))
    result=sval(row.get("ft_result")).upper()
    hg=as_int(row.get("ft_home_goals")); ag=as_int(row.get("ft_away_goals"))
    hp=result_points(result,"H"); ap=result_points(result,"A")
    if not home or not away or hg is None or ag is None or hp is None or ap is None:
        return False
    hs=states.setdefault(home,empty_team_state())
    as_=states.setdefault(away,empty_team_state())
    hs["played"]+=1; hs["points"]+=hp; hs["gf"]+=hg; hs["ga"]+=ag
    as_["played"]+=1; as_["points"]+=ap; as_["gf"]+=ag; as_["ga"]+=hg
    hs["history"].append({"day":current_day,"venue":"H","points":hp,"gf":hg,"ga":ag})
    as_["history"].append({"day":current_day,"venue":"A","points":ap,"gf":ag,"ga":hg})
    return True


def project(rows):
    parsed=[]; invalid_dates=0
    ids=set(); duplicate_ids=0
    for idx,row in enumerate(rows):
        day=parse_day(row.get("date_iso"))
        if day is None:
            invalid_dates+=1
            continue
        mid=sval(row.get("historical_match_id"))
        if mid:
            if mid in ids:
                duplicate_ids+=1
            ids.add(mid)
        parsed.append((sval(row.get("league_code")),sval(row.get("season_label")),day,idx,row))

    parsed.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
    outputs=[]; invalid_results=0
    coverage=defaultdict(int)

    groups=defaultdict(list)
    for league,season,day,idx,row in parsed:
        groups[(league,season,day)].append((idx,row))

    states_by_scope={}
    for scope_day in sorted(groups,key=lambda x:(x[0],x[1],x[2])):
        league,season,day=scope_day
        states=states_by_scope.setdefault((league,season),{})
        day_rows=groups[scope_day]

        for _,row in day_rows:
            feat=feature_row(row,day,states)
            outputs.append(feat)
            if feat["kickoff_minutes_local"]!="": coverage["kickoff"]+=1
            if feat["home_rest_days"]!="" and feat["away_rest_days"]!="": coverage["both_rest"]+=1
            if feat["home_rank_pre"]!="" and feat["away_rank_pre"]!="": coverage["both_rank"]+=1
            if int(feat["home_form_matches_last5"])>=5 and int(feat["away_form_matches_last5"])>=5:
                coverage["both_form5"]+=1
            if int(feat["home_form_matches_last10"])>=10 and int(feat["away_form_matches_last10"])>=10:
                coverage["both_form10"]+=1

        for _,row in day_rows:
            if not apply_result(row,day,states):
                invalid_results+=1

    outputs.sort(key=lambda r:(r["date_iso"],r["league_code"],r["home_team"],r["away_team"]))
    return outputs,{
        "invalid_date_rows":invalid_dates,
        "duplicate_historical_match_ids":duplicate_ids,
        "invalid_result_rows":invalid_results,
        "coverage":dict(coverage),
    }


def run(source,out_csv,meta_out):
    rows=load_rows(source)
    projected,diagnostics=project(rows)
    write_csv(out_csv,projected)
    leagues=sorted({r["league_code"] for r in projected})
    seasons=sorted({r["season_label"] for r in projected})
    coverage=diagnostics["coverage"]
    meta={
        "version":VERSION,"generated_at_utc":iso_now(),
        "status":"OK" if (
            len(projected)==len(rows)
            and diagnostics["invalid_date_rows"]==0
            and diagnostics["duplicate_historical_match_ids"]==0
            and diagnostics["invalid_result_rows"]==0
        ) else "ATTENTION",
        "source_rows":len(rows),"output_rows":len(projected),
        "unique_historical_match_ids":len({r["historical_match_id"] for r in projected if r["historical_match_id"]}),
        "league_codes":leagues,"season_labels":seasons,
        "invalid_date_rows":diagnostics["invalid_date_rows"],
        "duplicate_historical_match_ids":diagnostics["duplicate_historical_match_ids"],
        "invalid_result_rows":diagnostics["invalid_result_rows"],
        "rows_with_kickoff_time":coverage.get("kickoff",0),
        "rows_with_both_rest":coverage.get("both_rest",0),
        "rows_with_both_pre_match_rank":coverage.get("both_rank",0),
        "rows_with_both_full_last5":coverage.get("both_form5",0),
        "rows_with_both_full_last10":coverage.get("both_form10",0),
        "same_day_results_excluded":True,
        "same_day_leakage_policy":"All rows on a calendar date are projected before any result from that date updates state.",
        "no_lookahead":True,"provider_calls":0,"historical_backfill_only":True,
        "research_only":True,"operational_betting_authority":False,
        "creates_signal":False,"probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
    }
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.out_csv,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
