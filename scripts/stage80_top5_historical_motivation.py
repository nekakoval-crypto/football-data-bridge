#!/usr/bin/env python3
"""Stage80 — no-lookahead historical Top-5 standings/motivation context.

Reconstructs the league table strictly from matches on earlier calendar dates.
Same-day results are never visible to another match on that date.

This layer intentionally covers only facts that are safe to derive from the
season format contract and pre-match table:
- nominal matches remaining;
- title points distance and mathematical alive/eliminated state;
- relegation/playoff/safe position under the season rule contract;
- points distance to the current safety boundary;
- season phase and a deterministic title/survival proximity pressure bucket;
- whether a draw in the current fixture would already fail to preserve a
  theoretical points path to the current title/safety boundary.

European qualification remains UNKNOWN_BY_DESIGN because effective European
slots can depend on cup winners and UEFA access rules. The layer never calls a
provider, creates a betting signal, or grants model authority.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import standings_format_registry as format_registry
    from stage80_football_data_prematch_context import (
        apply_result,
        empty_team_state,
        parse_day,
        sval,
    )
except ImportError:  # pragma: no cover
    from scripts import standings_format_registry as format_registry
    from scripts.stage80_football_data_prematch_context import (
        apply_result,
        empty_team_state,
        parse_day,
        sval,
    )

VERSION="PBK_STAGE80_TOP5_HISTORICAL_MOTIVATION_CONTEXT_V1"
RANK_TIEBREAK_CONTRACT="POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1"
PRESSURE_ORDER={"UNKNOWN":-1,"NONE_VERIFIED":0,"LOW":1,"MEDIUM":2,"HIGH":3}

FIELDS=[
    "historical_match_id","league_code","season_label","date_iso","home_team","away_team",
    "format_status","team_count","total_games","safe_rank",
    "relegation_playoff_rank","direct_relegation_start_rank",
    "conditional_safety_playoff_if_tied","europe_status",
    "rank_tiebreak_contract","table_teams_with_history","full_table_available",
    "leader_points_pre","points_leaders_count",
    "safe_boundary_points_pre","danger_boundary_points_pre",
    "home_played_pre","away_played_pre","home_rank_pre","away_rank_pre",
    "home_points_pre","away_points_pre",
    "home_matches_remaining","away_matches_remaining",
    "home_season_phase","away_season_phase",
    "home_title_gap_points","away_title_gap_points",
    "home_title_status","away_title_status",
    "home_relegation_position_status","away_relegation_position_status",
    "home_points_to_safe_boundary","away_points_to_safe_boundary",
    "home_points_above_danger_boundary","away_points_above_danger_boundary",
    "home_relegation_math_status","away_relegation_math_status",
    "home_draw_eliminates_title_points_path","away_draw_eliminates_title_points_path",
    "home_draw_insufficient_to_reach_current_safe_points",
    "away_draw_insufficient_to_reach_current_safe_points",
    "home_primary_context","away_primary_context",
    "home_pressure","away_pressure","pressure_asymmetry",
    "boundary_tie_ambiguous","same_day_results_excluded","no_lookahead",
    "historical_backfill_only","research_only","operational_betting_authority",
    "creates_signal","probability_mutation","eligibility_mutation",
    "stake_changes","forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def write_json(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)


def btext(value):
    return "true" if bool(value) else "false"


def ranked_table(states):
    rows=[]
    for team,state in states.items():
        if int(state.get("played") or 0)<=0:
            continue
        points=int(state.get("points") or 0)
        gf=int(state.get("gf") or 0)
        ga=int(state.get("ga") or 0)
        rows.append({
            "team":team,
            "played":int(state.get("played") or 0),
            "points":points,
            "gf":gf,
            "ga":ga,
            "gd":gf-ga,
        })
    rows.sort(key=lambda x:(-x["points"],-x["gd"],-x["gf"],x["team"]))
    for i,row in enumerate(rows,1):
        row["rank"]=i
    return rows


def row_by_team(table,team):
    return next((r for r in table if r["team"]==team),None)


def row_by_rank(table,rank):
    return next((r for r in table if r["rank"]==rank),None)


def season_phase(played,total_games):
    if played is None or not total_games:
        return "UNKNOWN"
    progress=float(played)/float(total_games)
    if progress<0.40: return "EARLY"
    if progress<0.70: return "MID"
    if progress<0.90: return "LATE"
    return "RUN_IN"


def max_points(row,total_games):
    if not row or not total_games:
        return None
    return int(row["points"])+3*max(int(total_games)-int(row["played"]),0)


def draw_and_win_max(points,remaining):
    if remaining is None or remaining<=0:
        return None,None
    rest=max(remaining-1,0)
    return points+1+3*rest, points+3+3*rest


def pressure_for(*,phase,title_status,title_gap,position_status,points_to_safe,points_above_danger):
    title_relevant=(
        title_status in {"POINTS_LEADER","JOINT_POINTS_LEADER","ALIVE_BY_MAX_POINTS"}
        and title_gap is not None and title_gap<=6
    )
    survival_relevant=(
        position_status in {"IN_DIRECT_RELEGATION_ZONE","IN_RELEGATION_PLAYOFF_POSITION","BOUNDARY_TIE_AMBIGUOUS"}
        or (points_above_danger is not None and points_above_danger<=6)
        or (points_to_safe is not None and points_to_safe<=6 and points_to_safe>0)
    )
    if not title_relevant and not survival_relevant:
        return "NONE_VERIFIED","NO_TITLE_OR_RELEGATION_PRESSURE_VERIFIED"

    context="SURVIVAL" if survival_relevant else "TITLE"
    gaps=[]
    if title_relevant and title_gap is not None:
        gaps.append(title_gap)
    if survival_relevant:
        if points_to_safe is not None and points_to_safe>0:
            gaps.append(points_to_safe)
        elif points_above_danger is not None:
            gaps.append(points_above_danger)
    nearest=min(gaps) if gaps else None
    in_zone=position_status in {
        "IN_DIRECT_RELEGATION_ZONE","IN_RELEGATION_PLAYOFF_POSITION","BOUNDARY_TIE_AMBIGUOUS"
    }
    if phase in {"LATE","RUN_IN"} and (in_zone or (nearest is not None and nearest<=3)):
        return "HIGH",context
    if phase in {"LATE","RUN_IN"} and nearest is not None and nearest<=6:
        return "MEDIUM",context
    if in_zone or nearest is not None:
        return "LOW",context
    return "NONE_VERIFIED","NO_TITLE_OR_RELEGATION_PRESSURE_VERIFIED"


def team_context(team,table,fmt):
    row=row_by_team(table,team)
    if row is None:
        return {
            "played":0,"rank":None,"points":0,"remaining":fmt.get("total_games"),
            "phase":"UNKNOWN","title_gap":None,"title_status":"UNKNOWN",
            "position_status":"UNKNOWN","points_to_safe":None,"points_above_danger":None,
            "relegation_math_status":"UNKNOWN","draw_title_path":False,
            "draw_safe_path":False,"primary":"NO_TITLE_OR_RELEGATION_PRESSURE_VERIFIED",
            "pressure":"UNKNOWN",
        }

    total=fmt.get("total_games")
    team_count=fmt.get("team_count")
    full_table=(len(table)==team_count)
    played=row["played"]; points=row["points"]; rank=row["rank"]
    remaining=None if total is None else max(int(total)-played,0)
    phase=season_phase(played,total)

    result={
        "played":played,"rank":rank,"points":points,"remaining":remaining,"phase":phase,
        "title_gap":None,"title_status":"UNKNOWN","position_status":"UNKNOWN",
        "points_to_safe":None,"points_above_danger":None,
        "relegation_math_status":"UNKNOWN","draw_title_path":False,"draw_safe_path":False,
        "primary":"NO_TITLE_OR_RELEGATION_PRESSURE_VERIFIED","pressure":"UNKNOWN",
    }
    if not full_table or total is None:
        return result

    leader_points=table[0]["points"]
    leaders=[r for r in table if r["points"]==leader_points]
    team_max=max_points(row,total)
    title_gap=max(leader_points-points,0)
    if points==leader_points:
        title_status="JOINT_POINTS_LEADER" if len(leaders)>1 else "POINTS_LEADER"
    elif team_max is not None and team_max<leader_points:
        title_status="ELIMINATED_BY_MAX_POINTS"
    else:
        title_status="ALIVE_BY_MAX_POINTS"

    safe_rank=int(fmt["safe_rank"])
    playoff_rank=fmt.get("relegation_playoff_rank")
    direct_start=int(fmt["direct_relegation_start_rank"])
    danger_start=int(playoff_rank) if playoff_rank is not None else direct_start

    safe=row_by_rank(table,safe_rank)
    danger=row_by_rank(table,danger_start)
    safe_points=safe["points"] if safe else None
    danger_points=danger["points"] if danger else None
    boundary_tie=(
        safe_points is not None and danger_points is not None and safe_points==danger_points
        and points==safe_points
    )

    if boundary_tie:
        position="BOUNDARY_TIE_AMBIGUOUS"
    elif rank>=direct_start:
        position="IN_DIRECT_RELEGATION_ZONE"
    elif playoff_rank is not None and rank==int(playoff_rank):
        position="IN_RELEGATION_PLAYOFF_POSITION"
    else:
        position="CURRENTLY_SAFE_POSITION"

    points_to_safe=None if safe_points is None else max(safe_points-points,0)
    points_above_danger=None if danger_points is None else max(points-danger_points,0)

    danger_rows=[r for r in table if r["rank"]>=danger_start]
    danger_max=[max_points(r,total) for r in danger_rows]
    danger_max=[x for x in danger_max if x is not None]
    if position=="CURRENTLY_SAFE_POSITION" and danger_max and points>max(danger_max):
        math_status="POINTS_SAFE_FROM_RELEGATION_ZONE"
    elif position in {"IN_DIRECT_RELEGATION_ZONE","IN_RELEGATION_PLAYOFF_POSITION","BOUNDARY_TIE_AMBIGUOUS"}:
        if team_max is not None and safe_points is not None and team_max<safe_points:
            math_status="CANNOT_REACH_CURRENT_SAFE_POINTS"
        else:
            math_status="UNRESOLVED"
    else:
        math_status="UNRESOLVED"

    draw_max,win_max=draw_and_win_max(points,remaining)
    draw_title=bool(
        draw_max is not None and win_max is not None
        and draw_max<leader_points<=win_max
        and title_status!="ELIMINATED_BY_MAX_POINTS"
    )
    draw_safe=bool(
        position in {"IN_DIRECT_RELEGATION_ZONE","IN_RELEGATION_PLAYOFF_POSITION","BOUNDARY_TIE_AMBIGUOUS"}
        and safe_points is not None and draw_max is not None and win_max is not None
        and draw_max<safe_points<=win_max
    )

    pressure,primary=pressure_for(
        phase=phase,title_status=title_status,title_gap=title_gap,
        position_status=position,points_to_safe=points_to_safe,
        points_above_danger=points_above_danger,
    )
    result.update({
        "title_gap":title_gap,"title_status":title_status,
        "position_status":position,"points_to_safe":points_to_safe,
        "points_above_danger":points_above_danger,
        "relegation_math_status":math_status,
        "draw_title_path":draw_title,"draw_safe_path":draw_safe,
        "primary":primary,"pressure":pressure,
    })
    return result


def pressure_asymmetry(home,away):
    hp=PRESSURE_ORDER.get(home,-1); ap=PRESSURE_ORDER.get(away,-1)
    if hp<0 or ap<0:
        return "UNKNOWN"
    if hp>ap: return "HOME_HIGHER"
    if ap>hp: return "AWAY_HIGHER"
    return "BALANCED"


def feature_row(source,states):
    league=sval(source.get("league_code"))
    season=sval(source.get("season_label"))
    home=sval(source.get("home_team"))
    away=sval(source.get("away_team"))
    states.setdefault(home,empty_team_state())
    states.setdefault(away,empty_team_state())
    table=ranked_table(states)
    fmt=format_registry.get_historical_top5_format(league,season)
    h=team_context(home,table,fmt)
    a=team_context(away,table,fmt)

    team_count=fmt.get("team_count")
    full=(team_count is not None and len(table)==int(team_count))
    leader_points=table[0]["points"] if full and table else None
    leader_count=(
        sum(r["points"]==leader_points for r in table)
        if leader_points is not None else None
    )
    safe=row_by_rank(table,fmt.get("safe_rank")) if full else None
    danger_rank=(
        fmt.get("relegation_playoff_rank")
        if fmt.get("relegation_playoff_rank") is not None
        else fmt.get("direct_relegation_start_rank")
    )
    danger=row_by_rank(table,danger_rank) if full else None
    boundary_tie=bool(
        safe and danger and safe["points"]==danger["points"]
    )

    def out(value):
        return "" if value is None else value

    return {
        "historical_match_id":sval(source.get("historical_match_id")),
        "league_code":league,"season_label":season,"date_iso":sval(source.get("date_iso")),
        "home_team":home,"away_team":away,
        "format_status":fmt.get("status") or "UNKNOWN",
        "team_count":out(fmt.get("team_count")),"total_games":out(fmt.get("total_games")),
        "safe_rank":out(fmt.get("safe_rank")),
        "relegation_playoff_rank":out(fmt.get("relegation_playoff_rank")),
        "direct_relegation_start_rank":out(fmt.get("direct_relegation_start_rank")),
        "conditional_safety_playoff_if_tied":btext(fmt.get("conditional_safety_playoff_if_tied")),
        "europe_status":fmt.get("europe_status") or "UNKNOWN_BY_DESIGN",
        "rank_tiebreak_contract":RANK_TIEBREAK_CONTRACT,
        "table_teams_with_history":len(table),"full_table_available":btext(full),
        "leader_points_pre":out(leader_points),"points_leaders_count":out(leader_count),
        "safe_boundary_points_pre":out(safe["points"] if safe else None),
        "danger_boundary_points_pre":out(danger["points"] if danger else None),
        "home_played_pre":h["played"],"away_played_pre":a["played"],
        "home_rank_pre":out(h["rank"]),"away_rank_pre":out(a["rank"]),
        "home_points_pre":h["points"],"away_points_pre":a["points"],
        "home_matches_remaining":out(h["remaining"]),"away_matches_remaining":out(a["remaining"]),
        "home_season_phase":h["phase"],"away_season_phase":a["phase"],
        "home_title_gap_points":out(h["title_gap"]),"away_title_gap_points":out(a["title_gap"]),
        "home_title_status":h["title_status"],"away_title_status":a["title_status"],
        "home_relegation_position_status":h["position_status"],
        "away_relegation_position_status":a["position_status"],
        "home_points_to_safe_boundary":out(h["points_to_safe"]),
        "away_points_to_safe_boundary":out(a["points_to_safe"]),
        "home_points_above_danger_boundary":out(h["points_above_danger"]),
        "away_points_above_danger_boundary":out(a["points_above_danger"]),
        "home_relegation_math_status":h["relegation_math_status"],
        "away_relegation_math_status":a["relegation_math_status"],
        "home_draw_eliminates_title_points_path":btext(h["draw_title_path"]),
        "away_draw_eliminates_title_points_path":btext(a["draw_title_path"]),
        "home_draw_insufficient_to_reach_current_safe_points":btext(h["draw_safe_path"]),
        "away_draw_insufficient_to_reach_current_safe_points":btext(a["draw_safe_path"]),
        "home_primary_context":h["primary"],"away_primary_context":a["primary"],
        "home_pressure":h["pressure"],"away_pressure":a["pressure"],
        "pressure_asymmetry":pressure_asymmetry(h["pressure"],a["pressure"]),
        "boundary_tie_ambiguous":btext(boundary_tie),
        "same_day_results_excluded":"true","no_lookahead":"true",
        "historical_backfill_only":"true","research_only":"true",
        "operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
    }


def project(rows):
    parsed=[]; invalid_dates=0; ids=set(); duplicates=0
    for idx,row in enumerate(rows):
        day=parse_day(row.get("date_iso"))
        if day is None:
            invalid_dates+=1
            continue
        mid=sval(row.get("historical_match_id"))
        if mid in ids:
            duplicates+=1
        ids.add(mid)
        parsed.append((sval(row.get("league_code")),sval(row.get("season_label")),day,idx,row))

    groups=defaultdict(list)
    for league,season,day,idx,row in parsed:
        groups[(league,season,day)].append((idx,row))

    states_by_scope={}
    out=[]; invalid_results=0
    for key in sorted(groups,key=lambda x:(x[0],x[1],x[2])):
        league,season,day=key
        states=states_by_scope.setdefault((league,season),{})
        day_rows=groups[key]
        for _,row in day_rows:
            out.append(feature_row(row,states))
        for _,row in day_rows:
            if not apply_result(row,day,states):
                invalid_results+=1

    out.sort(key=lambda r:(r["date_iso"],r["league_code"],r["home_team"],r["away_team"]))
    return out,{
        "invalid_date_rows":invalid_dates,
        "duplicate_historical_match_ids":duplicates,
        "invalid_result_rows":invalid_results,
    }


def run(source,out_csv,meta_out):
    rows=read_csv(source)
    projected,diag=project(rows)
    write_csv(out_csv,projected)

    leagues=sorted({r["league_code"] for r in projected})
    seasons=sorted({r["season_label"] for r in projected})
    full=sum(r["full_table_available"]=="true" for r in projected)
    title_known=sum(r["home_title_status"]!="UNKNOWN" and r["away_title_status"]!="UNKNOWN" for r in projected)
    releg_known=sum(
        r["home_relegation_position_status"]!="UNKNOWN"
        and r["away_relegation_position_status"]!="UNKNOWN"
        for r in projected
    )
    tie_rows=sum(r["boundary_tie_ambiguous"]=="true" for r in projected)
    pressure=Counter(r["home_pressure"] for r in projected)
    pressure.update(r["away_pressure"] for r in projected)
    status="OK" if (
        len(rows)==16111 and len(projected)==16111
        and diag["invalid_date_rows"]==0
        and diag["duplicate_historical_match_ids"]==0
        and diag["invalid_result_rows"]==0
        and len({(r["league_code"],r["season_label"]) for r in projected})==45
        and all(r["format_status"]=="VERIFIED_RULE_CONTRACT" for r in projected)
        and all(r["europe_status"]=="UNKNOWN_BY_DESIGN" for r in projected)
    ) else "ATTENTION"

    meta={
        "version":VERSION,"generated_at_utc":iso_now(),"status":status,
        "source_rows":len(rows),"output_rows":len(projected),
        "unique_historical_match_ids":len({r["historical_match_id"] for r in projected}),
        "league_codes":leagues,"season_labels":seasons,"league_season_cells":45,
        **diag,
        "rows_with_full_table":full,
        "rows_with_both_title_status":title_known,
        "rows_with_both_relegation_status":releg_known,
        "rows_with_boundary_points_tie":tie_rows,
        "pressure_counts_team_sides":dict(sorted(pressure.items())),
        "format_contract":"TOP5_45_SEASON_CELLS_V1",
        "rank_tiebreak_contract":RANK_TIEBREAK_CONTRACT,
        "europe_status":"UNKNOWN_BY_DESIGN",
        "europe_reason":"European qualification boundaries are not inferred from final standings, cup winners or later UEFA access outcomes.",
        "must_win_semantics":"No generic MUST_WIN label is created. Only explicit draw-path mathematical flags against the current pre-match points boundary are emitted.",
        "same_day_results_excluded":True,
        "same_day_leakage_policy":"All matches on one calendar date are projected before any result from that date updates standings state.",
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
