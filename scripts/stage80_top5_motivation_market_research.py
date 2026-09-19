#!/usr/bin/env python3
"""Stage80 — descriptive Top-5 historical motivation × closing-market research.

Joins the 9-season Football-Data historical match matrix to the durable
no-lookahead Top-5 historical standings/motivation projection.

Factors are deliberately evidence-bound: pressure asymmetry, late title/survival
points proximity, current danger-zone side, and explicit draw-path mathematics.
Europe remains UNKNOWN_BY_DESIGN. No generic MUST_WIN or unmotivated label is
created or inferred.

Closing-market no-vig probabilities are market baselines only, never PBK
probabilities. This layer is descriptive research and cannot create betting/model
authority, eligibility, stakes, EV/value, or Forward journal entries.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION = "PBK_STAGE80_TOP5_MOTIVATION_MARKET_RESEARCH_V1"
TRUE_VALUES = {"1", "true", "yes", "y"}

FACTOR_NAMES = [
    "PRESSURE_ASYMMETRY",
    "HIGH_PRESSURE_SIDE",
    "MEDIUM_HIGH_PRESSURE_SIDE",
    "LATE_TITLE_NEAR_3_SIDE",
    "LATE_TITLE_NEAR_6_SIDE",
    "LATE_SURVIVAL_DANGER_SIDE",
    "LATE_SURVIVAL_WITHIN_3_SIDE",
    "LATE_SURVIVAL_WITHIN_6_SIDE",
    "DRAW_TITLE_PATH_SIDE",
    "DRAW_SAFE_PATH_SIDE",
]

OUT_FIELDS = [
    "factor","bucket","scope_type","scope_value","matches","sample_band",
    "home_wins","draws","away_wins","home_win_rate","draw_rate","away_win_rate",
    "avg_total_goals","over25_rate","btts_rate",
    "closing_1x2_matches","closing_1x2_avg_source_rows","closing_1x2_b365_source_rows",
    "closing_home_hit_rate","closing_draw_hit_rate","closing_away_hit_rate",
    "avg_market_novig_home","avg_market_novig_draw","avg_market_novig_away",
    "home_calibration_pp","draw_calibration_pp","away_calibration_pp",
    "home_flat_bet_roi_pct","draw_flat_bet_roi_pct","away_flat_bet_roi_pct",
    "closing_total25_matches","closing_total25_avg_source_rows","closing_total25_b365_source_rows",
    "closing_over25_hit_rate","closing_under25_hit_rate",
    "avg_market_novig_over25","avg_market_novig_under25",
    "over25_calibration_pp","under25_calibration_pp",
    "over25_flat_bet_roi_pct","under25_flat_bet_roi_pct",
    "research_only","operational_betting_authority","creates_signal",
    "probability_mutation","eligibility_mutation","stake_changes","forward_journal_mutation",
]

STABILITY_FIELDS = [
    "factor","bucket","scope_type","scope_value","seasons_with_matches","total_matches",
    "min_season_matches","max_season_matches",
    "home_roi_observed_seasons","home_roi_positive_seasons",
    "draw_roi_observed_seasons","draw_roi_positive_seasons",
    "away_roi_observed_seasons","away_roi_positive_seasons",
    "over25_roi_observed_seasons","over25_roi_positive_seasons",
    "under25_roi_observed_seasons","under25_roi_positive_seasons",
    "home_calibration_observed_seasons","home_calibration_positive_seasons",
    "over25_calibration_observed_seasons","over25_calibration_positive_seasons",
    "research_only","operational_betting_authority","creates_signal",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def sval(row,key):
    return str((row or {}).get(key) or "").strip()


def is_true(value):
    return str(value or "").strip().lower() in TRUE_VALUES


def fnum(value):
    try:
        n=float(str(value).strip())
        return n if math.isfinite(n) else None
    except (TypeError,ValueError):
        return None


def inum(value):
    n=fnum(value)
    return None if n is None else int(n)


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path,fields,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def write_json(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)


def pct(num,den,digits=3):
    return "" if not den else round(100.0*num/den,digits)


def rate(num,den,digits=5):
    return "" if not den else round(num/den,digits)


def avg(values,digits=5):
    vals=[v for v in values if v is not None]
    return "" if not vals else round(sum(vals)/len(vals),digits)


def sample_band(n):
    if n < 50:
        return "LT50"
    if n < 200:
        return "50_199"
    if n < 500:
        return "200_499"
    return "500_PLUS"


def valid_context(row):
    return (
        sval(row,"historical_match_id")
        and sval(row,"format_status")=="VERIFIED_RULE_CONTRACT"
        and sval(row,"europe_status")=="UNKNOWN_BY_DESIGN"
        and sval(row,"rank_tiebreak_contract")=="POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1"
        and is_true(row.get("same_day_results_excluded"))
        and is_true(row.get("no_lookahead"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    )


def select_triplet(row,avg_keys,b365_keys):
    for source,keys in (("AVG_CLOSE",avg_keys),("B365_CLOSE",b365_keys)):
        vals=[fnum(row.get(k)) for k in keys]
        if all(v is not None and v > 1.0 for v in vals):
            return source,vals
    return None,None


def novig(odds):
    inv=[1.0/o for o in odds]
    s=sum(inv)
    if s <= 0:
        return None
    return [x/s for x in inv]


def flat_return(hit,odds):
    return odds-1.0 if hit else -1.0


def side_bucket(home,away):
    if home and away:
        return "BOTH"
    if home:
        return "HOME_ONLY"
    if away:
        return "AWAY_ONLY"
    return "NEITHER"


def full_table(row):
    return is_true(row.get("full_table_available"))


def late_phase(row,side):
    return sval(row,f"{side}_season_phase") in {"LATE","RUN_IN"}


def title_near(row,side,limit):
    if not full_table(row) or not late_phase(row,side):
        return None
    status=sval(row,f"{side}_title_status")
    gap=inum(row.get(f"{side}_title_gap_points"))
    if status not in {"POINTS_LEADER","JOINT_POINTS_LEADER","ALIVE_BY_MAX_POINTS"}:
        return False
    return gap is not None and gap<=limit


def survival_danger(row,side):
    if not full_table(row) or not late_phase(row,side):
        return None
    return sval(row,f"{side}_relegation_position_status") in {
        "IN_DIRECT_RELEGATION_ZONE",
        "IN_RELEGATION_PLAYOFF_POSITION",
        "BOUNDARY_TIE_AMBIGUOUS",
    }


def survival_near(row,side,limit):
    if not full_table(row) or not late_phase(row,side):
        return None
    position=sval(row,f"{side}_relegation_position_status")
    if position in {
        "IN_DIRECT_RELEGATION_ZONE",
        "IN_RELEGATION_PLAYOFF_POSITION",
        "BOUNDARY_TIE_AMBIGUOUS",
    }:
        distance=inum(row.get(f"{side}_points_to_safe_boundary"))
    elif position=="CURRENTLY_SAFE_POSITION":
        distance=inum(row.get(f"{side}_points_above_danger_boundary"))
    else:
        return None
    return distance is not None and distance<=limit


def side_factor(row,home,away):
    if home is None or away is None:
        return "UNKNOWN"
    return side_bucket(bool(home),bool(away))


def factor_buckets(row):
    if not full_table(row):
        return {name:"UNKNOWN" for name in FACTOR_NAMES}

    pressure=sval(row,"pressure_asymmetry")
    if pressure not in {"HOME_HIGHER","AWAY_HIGHER","BALANCED"}:
        pressure="UNKNOWN"

    hp=sval(row,"home_pressure")
    ap=sval(row,"away_pressure")
    valid_pressures={"HIGH","MEDIUM","LOW","NONE_VERIFIED"}
    pressure_known=hp in valid_pressures and ap in valid_pressures

    return {
        "PRESSURE_ASYMMETRY":pressure,
        "HIGH_PRESSURE_SIDE":(
            side_bucket(hp=="HIGH",ap=="HIGH") if pressure_known else "UNKNOWN"
        ),
        "MEDIUM_HIGH_PRESSURE_SIDE":(
            side_bucket(hp in {"HIGH","MEDIUM"},ap in {"HIGH","MEDIUM"})
            if pressure_known else "UNKNOWN"
        ),
        "LATE_TITLE_NEAR_3_SIDE":side_factor(
            row,title_near(row,"home",3),title_near(row,"away",3)
        ),
        "LATE_TITLE_NEAR_6_SIDE":side_factor(
            row,title_near(row,"home",6),title_near(row,"away",6)
        ),
        "LATE_SURVIVAL_DANGER_SIDE":side_factor(
            row,survival_danger(row,"home"),survival_danger(row,"away")
        ),
        "LATE_SURVIVAL_WITHIN_3_SIDE":side_factor(
            row,survival_near(row,"home",3),survival_near(row,"away",3)
        ),
        "LATE_SURVIVAL_WITHIN_6_SIDE":side_factor(
            row,survival_near(row,"home",6),survival_near(row,"away",6)
        ),
        "DRAW_TITLE_PATH_SIDE":side_bucket(
            is_true(row.get("home_draw_eliminates_title_points_path")),
            is_true(row.get("away_draw_eliminates_title_points_path")),
        ),
        "DRAW_SAFE_PATH_SIDE":side_bucket(
            is_true(row.get("home_draw_insufficient_to_reach_current_safe_points")),
            is_true(row.get("away_draw_insufficient_to_reach_current_safe_points")),
        ),
    }


def enrich(matches,contexts):
    match_by_id={sval(r,"historical_match_id"):r for r in matches if sval(r,"historical_match_id")}
    context_by_id={sval(r,"historical_match_id"):r for r in contexts if sval(r,"historical_match_id")}
    invalid_context=sum(1 for r in contexts if not valid_context(r))
    joined=[]
    for mid,c in context_by_id.items():
        m=match_by_id.get(mid)
        if not m or not valid_context(c):
            continue
        result=sval(m,"ft_result").upper()
        hg=inum(m.get("ft_home_goals")); ag=inum(m.get("ft_away_goals"))
        if result not in {"H","D","A"} or hg is None or ag is None:
            continue
        row={**c}
        row["_result"]=result
        row["_hg"]=hg; row["_ag"]=ag
        row["_total"]=hg+ag
        row["_over25"]=(hg+ag)>2
        row["_btts"]=hg>0 and ag>0
        src1,odds1=select_triplet(
            m,["avg_close_home","avg_close_draw","avg_close_away"],
            ["b365_close_home","b365_close_draw","b365_close_away"]
        )
        if odds1:
            row["_1x2_source"]=src1
            row["_1x2_odds"]=odds1
            row["_1x2_novig"]=novig(odds1)
        srct,oddst=select_triplet(
            m,["avg_close_over_25","avg_close_under_25"],
            ["b365_close_over_25","b365_close_under_25"]
        )
        if oddst:
            row["_tot_source"]=srct
            row["_tot_odds"]=oddst
            row["_tot_novig"]=novig(oddst)
        joined.append(row)
    return joined,{
        "source_rows":len(matches),
        "context_rows":len(contexts),
        "source_unique_ids":len(match_by_id),
        "context_unique_ids":len(context_by_id),
        "invalid_context_governance_rows":invalid_context,
        "joined_rows":len(joined),
        "source_without_context":len(set(match_by_id)-set(context_by_id)),
        "context_without_source":len(set(context_by_id)-set(match_by_id)),
    }


def summarize(rows,factor,bucket,scope_type,scope_value):
    n=len(rows)
    h=sum(r["_result"]=="H" for r in rows)
    d=sum(r["_result"]=="D" for r in rows)
    a=sum(r["_result"]=="A" for r in rows)
    o25=sum(r["_over25"] for r in rows)
    btts=sum(r["_btts"] for r in rows)

    one=[r for r in rows if r.get("_1x2_odds") and r.get("_1x2_novig")]
    hret=[]; dret=[]; aret=[]
    for r in one:
        odds=r["_1x2_odds"]
        hret.append(flat_return(r["_result"]=="H",odds[0]))
        dret.append(flat_return(r["_result"]=="D",odds[1]))
        aret.append(flat_return(r["_result"]=="A",odds[2]))
    hhit=sum(r["_result"]=="H" for r in one)
    dhit=sum(r["_result"]=="D" for r in one)
    ahit=sum(r["_result"]=="A" for r in one)
    hp=avg([r["_1x2_novig"][0] for r in one])
    dp=avg([r["_1x2_novig"][1] for r in one])
    ap=avg([r["_1x2_novig"][2] for r in one])

    totals=[r for r in rows if r.get("_tot_odds") and r.get("_tot_novig")]
    oret=[]; uret=[]
    for r in totals:
        odds=r["_tot_odds"]
        oret.append(flat_return(r["_over25"],odds[0]))
        uret.append(flat_return(not r["_over25"],odds[1]))
    ohit=sum(r["_over25"] for r in totals)
    uhit=len(totals)-ohit
    op=avg([r["_tot_novig"][0] for r in totals])
    up=avg([r["_tot_novig"][1] for r in totals])

    def calibration(hit,count,market):
        if not count or market=="":
            return ""
        return round(100.0*(hit/count-float(market)),3)

    def roi(values):
        return "" if not values else round(100.0*sum(values)/len(values),3)

    return {
        "factor":factor,"bucket":bucket,"scope_type":scope_type,"scope_value":scope_value,
        "matches":n,"sample_band":sample_band(n),
        "home_wins":h,"draws":d,"away_wins":a,
        "home_win_rate":rate(h,n),"draw_rate":rate(d,n),"away_win_rate":rate(a,n),
        "avg_total_goals":avg([r["_total"] for r in rows],3),
        "over25_rate":rate(o25,n),"btts_rate":rate(btts,n),
        "closing_1x2_matches":len(one),
        "closing_1x2_avg_source_rows":sum(r.get("_1x2_source")=="AVG_CLOSE" for r in one),
        "closing_1x2_b365_source_rows":sum(r.get("_1x2_source")=="B365_CLOSE" for r in one),
        "closing_home_hit_rate":rate(hhit,len(one)),
        "closing_draw_hit_rate":rate(dhit,len(one)),
        "closing_away_hit_rate":rate(ahit,len(one)),
        "avg_market_novig_home":hp,"avg_market_novig_draw":dp,"avg_market_novig_away":ap,
        "home_calibration_pp":calibration(hhit,len(one),hp),
        "draw_calibration_pp":calibration(dhit,len(one),dp),
        "away_calibration_pp":calibration(ahit,len(one),ap),
        "home_flat_bet_roi_pct":roi(hret),"draw_flat_bet_roi_pct":roi(dret),"away_flat_bet_roi_pct":roi(aret),
        "closing_total25_matches":len(totals),
        "closing_total25_avg_source_rows":sum(r.get("_tot_source")=="AVG_CLOSE" for r in totals),
        "closing_total25_b365_source_rows":sum(r.get("_tot_source")=="B365_CLOSE" for r in totals),
        "closing_over25_hit_rate":rate(ohit,len(totals)),
        "closing_under25_hit_rate":rate(uhit,len(totals)),
        "avg_market_novig_over25":op,"avg_market_novig_under25":up,
        "over25_calibration_pp":calibration(ohit,len(totals),op),
        "under25_calibration_pp":calibration(uhit,len(totals),up),
        "over25_flat_bet_roi_pct":roi(oret),"under25_flat_bet_roi_pct":roi(uret),
        "research_only":"true","operational_betting_authority":"false","creates_signal":"false",
        "probability_mutation":"false","eligibility_mutation":"false","stake_changes":"false",
        "forward_journal_mutation":"false",
    }


def scope_keys(row):
    league=sval(row,"league_code")
    season=sval(row,"season_label")
    return [
        ("ALL","ALL"),
        ("LEAGUE",league),
        ("SEASON",season),
        ("LEAGUE_SEASON",f"{league}|{season}"),
    ]


def aggregate(joined):
    groups=defaultdict(list)
    for row in joined:
        buckets=factor_buckets(row)
        for factor,bucket in buckets.items():
            for scope_type,scope_value in scope_keys(row):
                groups[(factor,bucket,scope_type,scope_value)].append(row)
    out=[
        summarize(rows,*key)
        for key,rows in sorted(groups.items())
    ]
    return out


def stability(joined):
    base=defaultdict(lambda: defaultdict(list))
    for row in joined:
        season=sval(row,"season_label")
        league=sval(row,"league_code")
        for factor,bucket in factor_buckets(row).items():
            base[(factor,bucket,"ALL","ALL")][season].append(row)
            base[(factor,bucket,"LEAGUE",league)][season].append(row)

    rows=[]
    for key,seasons in sorted(base.items()):
        season_summaries=[]
        for season,items in sorted(seasons.items()):
            season_summaries.append(summarize(items,key[0],key[1],"SEASON",season))
        def count_observed(field):
            return sum(s[field] != "" for s in season_summaries)
        def count_positive(field):
            return sum(s[field] != "" and float(s[field]) > 0 for s in season_summaries)
        sizes=[int(s["matches"]) for s in season_summaries]
        rows.append({
            "factor":key[0],"bucket":key[1],"scope_type":key[2],"scope_value":key[3],
            "seasons_with_matches":len(season_summaries),"total_matches":sum(sizes),
            "min_season_matches":min(sizes) if sizes else 0,"max_season_matches":max(sizes) if sizes else 0,
            "home_roi_observed_seasons":count_observed("home_flat_bet_roi_pct"),
            "home_roi_positive_seasons":count_positive("home_flat_bet_roi_pct"),
            "draw_roi_observed_seasons":count_observed("draw_flat_bet_roi_pct"),
            "draw_roi_positive_seasons":count_positive("draw_flat_bet_roi_pct"),
            "away_roi_observed_seasons":count_observed("away_flat_bet_roi_pct"),
            "away_roi_positive_seasons":count_positive("away_flat_bet_roi_pct"),
            "over25_roi_observed_seasons":count_observed("over25_flat_bet_roi_pct"),
            "over25_roi_positive_seasons":count_positive("over25_flat_bet_roi_pct"),
            "under25_roi_observed_seasons":count_observed("under25_flat_bet_roi_pct"),
            "under25_roi_positive_seasons":count_positive("under25_flat_bet_roi_pct"),
            "home_calibration_observed_seasons":count_observed("home_calibration_pp"),
            "home_calibration_positive_seasons":count_positive("home_calibration_pp"),
            "over25_calibration_observed_seasons":count_observed("over25_calibration_pp"),
            "over25_calibration_positive_seasons":count_positive("over25_calibration_pp"),
            "research_only":"true","operational_betting_authority":"false","creates_signal":"false",
        })
    return rows


def run(matches_path,context_path,out_csv,stability_out,meta_out):
    matches=read_csv(matches_path)
    contexts=read_csv(context_path)
    joined,diag=enrich(matches,contexts)
    profiles=aggregate(joined)
    stable=stability(joined)

    closing_1x2=sum(bool(r.get("_1x2_odds")) for r in joined)
    closing_total=sum(bool(r.get("_tot_odds")) for r in joined)
    status="OK" if (
        diag["source_rows"]==16111
        and diag["context_rows"]==16111
        and diag["source_unique_ids"]==16111
        and diag["context_unique_ids"]==16111
        and diag["joined_rows"]==16111
        and diag["invalid_context_governance_rows"]==0
        and diag["source_without_context"]==0
        and diag["context_without_source"]==0
    ) else "ATTENTION"

    meta={
        "version":VERSION,"generated_at_utc":iso_now(),"status":status,
        **diag,
        "factor_names":FACTOR_NAMES,
        "factor_profile_rows":len(profiles),
        "season_stability_rows":len(stable),
        "closing_1x2_matches":closing_1x2,
        "closing_total25_matches":closing_total,
        "closing_odds_policy":"AVG_CLOSE preferred; B365_CLOSE fallback. Opening and closing odds are never mixed in one observation.",
        "market_probability_semantics":"No-vig probabilities are derived from historical closing market odds and are not PBK probabilities.",
        "motivation_contract":"TOP5_HISTORICAL_MOTIVATION_V1_NO_LOOKAHEAD",
        "rank_tiebreak_contract":"POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1",
        "europe_status":"UNKNOWN_BY_DESIGN",
        "generic_must_win_created":False,
        "unmotivated_label_created":False,
        "research_only":True,"operational_betting_authority":False,
        "creates_signal":False,"promotes_factor":False,
        "probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,"provider_calls":0,
    }
    write_csv(out_csv,OUT_FIELDS,profiles)
    write_csv(stability_out,STABILITY_FIELDS,stable)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--matches",required=True)
    p.add_argument("--context",required=True,help="Top-5 historical motivation CSV")
    p.add_argument("--out-csv",required=True)
    p.add_argument("--stability-out",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.matches,a.context,a.out_csv,a.stability_out,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
