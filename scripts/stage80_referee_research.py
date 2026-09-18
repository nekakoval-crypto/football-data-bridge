#!/usr/bin/env python3
"""Stage80 — EPL referee research projections from normalized Football-Data history.

Research-only historical enrichment. No provider calls, no betting/model authority,
no causal or bias claims. Missing source metrics remain UNKNOWN and are never
zero-filled.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION = "PBK_STAGE80_EPL_REFEREE_RESEARCH_V1"

PROFILE_FIELDS = [
    "referee","matches","season_count","first_date","last_date","unique_teams",
    "home_wins","draws","away_wins","home_win_pct","draw_pct","away_win_pct",
    "goal_observed_matches","total_goals","goals_per_observed_match",
    "yellow_observed_matches","home_yellows","away_yellows","total_yellows",
    "home_yellows_per_observed_match","away_yellows_per_observed_match",
    "total_yellows_per_observed_match","home_minus_away_yellows_per_observed_match",
    "red_observed_matches","home_reds","away_reds","total_reds",
    "home_reds_per_observed_match","away_reds_per_observed_match",
    "total_reds_per_observed_match","home_minus_away_reds_per_observed_match",
    "foul_observed_matches","home_fouls","away_fouls","total_fouls",
    "home_fouls_per_observed_match","away_fouls_per_observed_match",
    "total_fouls_per_observed_match","home_minus_away_fouls_per_observed_match",
    "source_scope","penalties_available","research_only","operational_betting_authority",
]

TEAM_FIELDS = [
    "referee","team","matches","home_matches","away_matches","wins","draws","losses",
    "win_pct","draw_pct","loss_pct","points","points_per_match",
    "goal_observed_matches","goals_for","goals_against","goal_difference",
    "yellow_observed_matches","yellows_for","yellows_against","yellow_difference",
    "red_observed_matches","reds_for","reds_against","red_difference",
    "foul_observed_matches","fouls_for","fouls_against","foul_difference",
    "first_date","last_date","season_count",
    "source_scope","penalties_available","research_only","operational_betting_authority",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def text(value):
    return str(value or "").strip()


def as_int(value):
    raw=text(value)
    if raw=="":
        return None
    try:
        return int(float(raw))
    except (TypeError,ValueError):
        return None


def pct(num,den):
    return round(100.0*num/den,2) if den else 0.0


def rate(num,den):
    return round(num/den,3) if den else None


def load_source(path):
    rows=[]
    with Path(path).open(encoding="utf-8-sig",newline="") as stream:
        for row in csv.DictReader(stream):
            referee=text(row.get("referee"))
            if not referee:
                continue
            if text(row.get("league_code"))!="E0":
                continue
            rows.append(row)
    return rows


def _metric_pair(row,home_key,away_key):
    home=as_int(row.get(home_key)); away=as_int(row.get(away_key))
    return (home,away) if home is not None and away is not None else None


def aggregate_referees(rows):
    data={}
    for row in rows:
        referee=text(row.get("referee"))
        rec=data.setdefault(referee,{
            "matches":0,"seasons":set(),"dates":[],"teams":set(),
            "home_wins":0,"draws":0,"away_wins":0,
            "goal_observed_matches":0,"total_goals":0,
            "yellow_observed_matches":0,"home_yellows":0,"away_yellows":0,
            "red_observed_matches":0,"home_reds":0,"away_reds":0,
            "foul_observed_matches":0,"home_fouls":0,"away_fouls":0,
        })
        rec["matches"]+=1
        rec["seasons"].add(text(row.get("season_label")))
        date=text(row.get("date_iso"))
        if date: rec["dates"].append(date)
        home=text(row.get("home_team")); away=text(row.get("away_team"))
        if home: rec["teams"].add(home)
        if away: rec["teams"].add(away)
        result=text(row.get("ft_result"))
        if result=="H": rec["home_wins"]+=1
        elif result=="D": rec["draws"]+=1
        elif result=="A": rec["away_wins"]+=1

        pair=_metric_pair(row,"ft_home_goals","ft_away_goals")
        if pair:
            rec["goal_observed_matches"]+=1
            rec["total_goals"]+=pair[0]+pair[1]
        pair=_metric_pair(row,"home_yellows","away_yellows")
        if pair:
            rec["yellow_observed_matches"]+=1
            rec["home_yellows"]+=pair[0]; rec["away_yellows"]+=pair[1]
        pair=_metric_pair(row,"home_reds","away_reds")
        if pair:
            rec["red_observed_matches"]+=1
            rec["home_reds"]+=pair[0]; rec["away_reds"]+=pair[1]
        pair=_metric_pair(row,"home_fouls","away_fouls")
        if pair:
            rec["foul_observed_matches"]+=1
            rec["home_fouls"]+=pair[0]; rec["away_fouls"]+=pair[1]

    out=[]
    for referee,rec in sorted(data.items()):
        m=rec["matches"]; yo=rec["yellow_observed_matches"]; ro=rec["red_observed_matches"]; fo=rec["foul_observed_matches"]
        out.append({
            "referee":referee,"matches":m,"season_count":len([x for x in rec["seasons"] if x]),
            "first_date":min(rec["dates"]) if rec["dates"] else "","last_date":max(rec["dates"]) if rec["dates"] else "",
            "unique_teams":len(rec["teams"]),
            "home_wins":rec["home_wins"],"draws":rec["draws"],"away_wins":rec["away_wins"],
            "home_win_pct":pct(rec["home_wins"],m),"draw_pct":pct(rec["draws"],m),"away_win_pct":pct(rec["away_wins"],m),
            "goal_observed_matches":rec["goal_observed_matches"],"total_goals":rec["total_goals"],
            "goals_per_observed_match":rate(rec["total_goals"],rec["goal_observed_matches"]),
            "yellow_observed_matches":yo,"home_yellows":rec["home_yellows"],"away_yellows":rec["away_yellows"],
            "total_yellows":rec["home_yellows"]+rec["away_yellows"],
            "home_yellows_per_observed_match":rate(rec["home_yellows"],yo),
            "away_yellows_per_observed_match":rate(rec["away_yellows"],yo),
            "total_yellows_per_observed_match":rate(rec["home_yellows"]+rec["away_yellows"],yo),
            "home_minus_away_yellows_per_observed_match":rate(rec["home_yellows"]-rec["away_yellows"],yo),
            "red_observed_matches":ro,"home_reds":rec["home_reds"],"away_reds":rec["away_reds"],
            "total_reds":rec["home_reds"]+rec["away_reds"],
            "home_reds_per_observed_match":rate(rec["home_reds"],ro),
            "away_reds_per_observed_match":rate(rec["away_reds"],ro),
            "total_reds_per_observed_match":rate(rec["home_reds"]+rec["away_reds"],ro),
            "home_minus_away_reds_per_observed_match":rate(rec["home_reds"]-rec["away_reds"],ro),
            "foul_observed_matches":fo,"home_fouls":rec["home_fouls"],"away_fouls":rec["away_fouls"],
            "total_fouls":rec["home_fouls"]+rec["away_fouls"],
            "home_fouls_per_observed_match":rate(rec["home_fouls"],fo),
            "away_fouls_per_observed_match":rate(rec["away_fouls"],fo),
            "total_fouls_per_observed_match":rate(rec["home_fouls"]+rec["away_fouls"],fo),
            "home_minus_away_fouls_per_observed_match":rate(rec["home_fouls"]-rec["away_fouls"],fo),
            "source_scope":"EPL_ONLY","penalties_available":"false","research_only":"true",
            "operational_betting_authority":"false",
        })
    return out


def aggregate_team_splits(rows):
    data={}
    for row in rows:
        referee=text(row.get("referee")); home=text(row.get("home_team")); away=text(row.get("away_team"))
        result=text(row.get("ft_result")); season=text(row.get("season_label")); date=text(row.get("date_iso"))
        metrics={
            "goals":_metric_pair(row,"ft_home_goals","ft_away_goals"),
            "yellow":_metric_pair(row,"home_yellows","away_yellows"),
            "red":_metric_pair(row,"home_reds","away_reds"),
            "foul":_metric_pair(row,"home_fouls","away_fouls"),
        }
        for team,side in ((home,"H"),(away,"A")):
            if not team: continue
            rec=data.setdefault((referee,team),{
                "matches":0,"home_matches":0,"away_matches":0,"wins":0,"draws":0,"losses":0,"points":0,
                "goal_observed_matches":0,"goals_for":0,"goals_against":0,
                "yellow_observed_matches":0,"yellows_for":0,"yellows_against":0,
                "red_observed_matches":0,"reds_for":0,"reds_against":0,
                "foul_observed_matches":0,"fouls_for":0,"fouls_against":0,
                "dates":[],"seasons":set(),
            })
            rec["matches"]+=1; rec["home_matches" if side=="H" else "away_matches"]+=1
            if date: rec["dates"].append(date)
            if season: rec["seasons"].add(season)
            won=(result=="H" and side=="H") or (result=="A" and side=="A")
            lost=(result=="A" and side=="H") or (result=="H" and side=="A")
            if won: rec["wins"]+=1; rec["points"]+=3
            elif result=="D": rec["draws"]+=1; rec["points"]+=1
            elif lost: rec["losses"]+=1

            for metric,pair in metrics.items():
                if not pair: continue
                rec[f"{metric}_observed_matches"]+=1
                own,opp=(pair[0],pair[1]) if side=="H" else (pair[1],pair[0])
                if metric=="goals":
                    rec["goals_for"]+=own; rec["goals_against"]+=opp
                elif metric=="yellow":
                    rec["yellows_for"]+=own; rec["yellows_against"]+=opp
                elif metric=="red":
                    rec["reds_for"]+=own; rec["reds_against"]+=opp
                elif metric=="foul":
                    rec["fouls_for"]+=own; rec["fouls_against"]+=opp

    out=[]
    for (referee,team),rec in sorted(data.items()):
        m=rec["matches"]
        out.append({
            "referee":referee,"team":team,"matches":m,"home_matches":rec["home_matches"],"away_matches":rec["away_matches"],
            "wins":rec["wins"],"draws":rec["draws"],"losses":rec["losses"],
            "win_pct":pct(rec["wins"],m),"draw_pct":pct(rec["draws"],m),"loss_pct":pct(rec["losses"],m),
            "points":rec["points"],"points_per_match":rate(rec["points"],m),
            "goal_observed_matches":rec["goal_observed_matches"],"goals_for":rec["goals_for"],"goals_against":rec["goals_against"],
            "goal_difference":rec["goals_for"]-rec["goals_against"],
            "yellow_observed_matches":rec["yellow_observed_matches"],"yellows_for":rec["yellows_for"],"yellows_against":rec["yellows_against"],
            "yellow_difference":rec["yellows_for"]-rec["yellows_against"],
            "red_observed_matches":rec["red_observed_matches"],"reds_for":rec["reds_for"],"reds_against":rec["reds_against"],
            "red_difference":rec["reds_for"]-rec["reds_against"],
            "foul_observed_matches":rec["foul_observed_matches"],"fouls_for":rec["fouls_for"],"fouls_against":rec["fouls_against"],
            "foul_difference":rec["fouls_for"]-rec["fouls_against"],
            "first_date":min(rec["dates"]) if rec["dates"] else "","last_date":max(rec["dates"]) if rec["dates"] else "",
            "season_count":len(rec["seasons"]),"source_scope":"EPL_ONLY","penalties_available":"false",
            "research_only":"true","operational_betting_authority":"false",
        })
    return out


def write_csv(path,fields,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def run(source,profiles_out,team_splits_out,meta_out):
    rows=load_source(source)
    profiles=aggregate_referees(rows)
    team_splits=aggregate_team_splits(rows)
    write_csv(profiles_out,PROFILE_FIELDS,profiles)
    write_csv(team_splits_out,TEAM_FIELDS,team_splits)
    meta={
        "version":VERSION,"generated_at_utc":iso_now(),"status":"OK",
        "source_scope":"EPL_ONLY","source_rows":len(rows),"unique_referees":len(profiles),
        "referee_team_pairs":len(team_splits),
        "profile_match_sum":sum(int(r["matches"]) for r in profiles),
        "team_split_match_sum":sum(int(r["matches"]) for r in team_splits),
        "penalties_available":False,
        "missing_metrics_remain_unknown":True,
        "research_only":True,"operational_betting_authority":False,
        "creates_signal":False,"probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,"provider_calls":0,
    }
    Path(meta_out).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--profiles-out",required=True)
    p.add_argument("--team-splits-out",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.profiles_out,a.team_splits_out,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
