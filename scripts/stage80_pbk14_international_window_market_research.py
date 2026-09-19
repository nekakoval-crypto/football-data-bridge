#!/usr/bin/env python3
"""Stage80 — descriptive PBK14 international-window market research.

Input is the durable strict AUTO/HIGH PBK14 historical-market × PBK16
international-window join V2.

Research questions are intentionally calendar-level only:
- <=72h / <=96h / <=7d before an international window;
- <=72h / <=96h / <=7d after an international window;
- whether home/away/both are playing their first domestic-league match after it;
- BEFORE / INSIDE / AFTER relation to the nearest window;
- fixed-window maximum match count as calendar intensity, never player usage.

Outputs descriptive outcome/goal/BTTS rates plus closing-market no-vig
calibration and flat-bet ROI for 1X2 and O/U2.5.

Calendar proximity or window length never proves that any player was called up,
travelled, appeared or played minutes. No factor is ranked, selected, promoted
or given operational authority here.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_PBK14_INTERNATIONAL_WINDOW_MARKET_RESEARCH_V1"

FACTORS=[
    "INTL_BEFORE_72H",
    "INTL_BEFORE_96H",
    "INTL_BEFORE_7D",
    "INTL_AFTER_72H",
    "INTL_AFTER_96H",
    "INTL_AFTER_7D",
    "FIRST_DOMESTIC_AFTER_SIDE",
    "WINDOW_RELATION",
    "WINDOW_MAX_MATCHES",
]

PROFILE_FIELDS=[
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
    "promotes_factor","probability_mutation","eligibility_mutation",
    "stake_changes","forward_journal_mutation",
]

STABILITY_FIELDS=[
    "factor","bucket","scope_type","scope_value",
    "seasons_with_matches","total_matches","min_season_matches","max_season_matches",
    "home_roi_observed_seasons","home_roi_positive_seasons",
    "draw_roi_observed_seasons","draw_roi_positive_seasons",
    "away_roi_observed_seasons","away_roi_positive_seasons",
    "over25_roi_observed_seasons","over25_roi_positive_seasons",
    "under25_roi_observed_seasons","under25_roi_positive_seasons",
    "home_calibration_observed_seasons","home_calibration_positive_seasons",
    "away_calibration_observed_seasons","away_calibration_positive_seasons",
    "over25_calibration_observed_seasons","over25_calibration_positive_seasons",
    "research_only","operational_betting_authority","creates_signal","promotes_factor",
]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def sval(row,key):
    return str((row or {}).get(key) or "").strip()


def is_true(value):
    return str(value or "").strip().lower() in {"1","true","yes","y"}


def is_false(value):
    return str(value or "").strip().lower() in {"0","false","no","n"}


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


def avg(values,digits=5):
    vals=[v for v in values if v is not None]
    return "" if not vals else round(sum(vals)/len(vals),digits)


def rate(num,den,digits=5):
    return "" if not den else round(num/den,digits)


def sample_band(n):
    if n<50: return "LT50"
    if n<200: return "50_199"
    if n<500: return "200_499"
    return "500_PLUS"


def select_triplet(row,avg_keys,b365_keys):
    for source,keys in (("AVG_CLOSE",avg_keys),("B365_CLOSE",b365_keys)):
        vals=[fnum(row.get(k)) for k in keys]
        if all(v is not None and v>1.0 for v in vals):
            return source,vals
    return None,None


def novig(odds):
    inv=[1.0/o for o in odds]
    s=sum(inv)
    return None if s<=0 else [x/s for x in inv]


def flat_return(hit,odds):
    return odds-1.0 if hit else -1.0


def valid_row(row):
    return (
        sval(row,"historical_match_id")
        and sval(row,"api_fixture_id")
        and sval(row,"mapping_status") in {"AUTO","HIGH"}
        and sval(row,"fuzzy_string_matching_used")=="false"
        and is_true(row.get("one_to_one_verified"))
        and sval(row,"window_reference_contract")=="NEAREST_WINDOW_RELATION_GATED_V2"
        and sval(row,"player_level_international_status")=="UNVERIFIED"
        and is_false(row.get("final_tournaments_included"))
        and is_false(row.get("non_uefa_only_windows_included"))
        and is_true(row.get("calendar_level_only"))
        and is_true(row.get("as_known_calendar_reference"))
        and is_true(row.get("no_match_result_dependency"))
        and is_true(row.get("no_lookahead"))
        and str(row.get("context_provider_calls") or "").strip()=="0"
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    )


def side_bucket(home,away):
    if home and away: return "BOTH"
    if home: return "HOME_ONLY"
    if away: return "AWAY_ONLY"
    return "NEITHER"


def flag_bucket(row,key):
    return "WITHIN" if is_true(row.get(key)) else "OUTSIDE"


def factor_buckets(row):
    relation=sval(row,"window_relation").upper()
    if relation not in {"BEFORE","INSIDE","AFTER"}:
        relation="UNKNOWN"

    max_matches=inum(row.get("window_max_matches"))
    max_bucket=f"MAX_{max_matches}" if max_matches in {2,3,4} else "UNKNOWN"

    return {
        "INTL_BEFORE_72H":flag_bucket(row,"within_72h_before_window"),
        "INTL_BEFORE_96H":flag_bucket(row,"within_96h_before_window"),
        "INTL_BEFORE_7D":flag_bucket(row,"within_7d_before_window"),
        "INTL_AFTER_72H":flag_bucket(row,"within_72h_after_window"),
        "INTL_AFTER_96H":flag_bucket(row,"within_96h_after_window"),
        "INTL_AFTER_7D":flag_bucket(row,"within_7d_after_window"),
        "FIRST_DOMESTIC_AFTER_SIDE":side_bucket(
            is_true(row.get("home_first_domestic_league_match_after_window")),
            is_true(row.get("away_first_domestic_league_match_after_window")),
        ),
        "WINDOW_RELATION":relation,
        "WINDOW_MAX_MATCHES":max_bucket,
    }


def enrich(rows):
    out=[]
    invalid=0
    for row in rows:
        if not valid_row(row):
            invalid+=1
            continue
        result=sval(row,"ft_result").upper()
        hg=inum(row.get("ft_home_goals")); ag=inum(row.get("ft_away_goals"))
        if result not in {"H","D","A"} or hg is None or ag is None:
            invalid+=1
            continue
        item=dict(row)
        item["_result"]=result
        item["_hg"]=hg; item["_ag"]=ag
        item["_total"]=hg+ag
        item["_over25"]=(hg+ag)>2
        item["_btts"]=hg>0 and ag>0

        src1,odds1=select_triplet(
            row,
            ["avg_close_home","avg_close_draw","avg_close_away"],
            ["b365_close_home","b365_close_draw","b365_close_away"],
        )
        if odds1:
            item["_1x2_source"]=src1
            item["_1x2_odds"]=odds1
            item["_1x2_novig"]=novig(odds1)

        srct,oddst=select_triplet(
            row,
            ["avg_close_over_25","avg_close_under_25"],
            ["b365_close_over_25","b365_close_under_25"],
        )
        if oddst:
            item["_tot_source"]=srct
            item["_tot_odds"]=oddst
            item["_tot_novig"]=novig(oddst)
        out.append(item)
    return out,invalid


def scope_keys(row):
    league=sval(row,"league_code")
    season=sval(row,"season_start")
    return [
        ("ALL","ALL"),
        ("LEAGUE",league),
        ("SEASON",season),
        ("LEAGUE_SEASON",f"{league}|{season}"),
    ]


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
        "home_flat_bet_roi_pct":roi(hret),
        "draw_flat_bet_roi_pct":roi(dret),
        "away_flat_bet_roi_pct":roi(aret),
        "closing_total25_matches":len(totals),
        "closing_total25_avg_source_rows":sum(r.get("_tot_source")=="AVG_CLOSE" for r in totals),
        "closing_total25_b365_source_rows":sum(r.get("_tot_source")=="B365_CLOSE" for r in totals),
        "closing_over25_hit_rate":rate(ohit,len(totals)),
        "closing_under25_hit_rate":rate(uhit,len(totals)),
        "avg_market_novig_over25":op,"avg_market_novig_under25":up,
        "over25_calibration_pp":calibration(ohit,len(totals),op),
        "under25_calibration_pp":calibration(uhit,len(totals),up),
        "over25_flat_bet_roi_pct":roi(oret),
        "under25_flat_bet_roi_pct":roi(uret),
        "research_only":"true","operational_betting_authority":"false",
        "creates_signal":"false","promotes_factor":"false",
        "probability_mutation":"false","eligibility_mutation":"false",
        "stake_changes":"false","forward_journal_mutation":"false",
    }


def aggregate(joined):
    groups=defaultdict(list)
    for row in joined:
        for factor,bucket in factor_buckets(row).items():
            for scope_type,scope_value in scope_keys(row):
                groups[(factor,bucket,scope_type,scope_value)].append(row)
    return [
        summarize(rows,*key)
        for key,rows in sorted(groups.items())
    ]


def stability(joined):
    by=defaultdict(lambda:defaultdict(list))
    for row in joined:
        season=sval(row,"season_start")
        for factor,bucket in factor_buckets(row).items():
            by[(factor,bucket,"ALL","ALL")][season].append(row)
            league=sval(row,"league_code")
            by[(factor,bucket,"LEAGUE",league)][season].append(row)

    out=[]
    for key,seasons in sorted(by.items()):
        profiles=[summarize(rows,key[0],key[1],key[2],key[3]) for _,rows in sorted(seasons.items())]
        matches=[p["matches"] for p in profiles]

        def observed(field):
            return [p for p in profiles if p.get(field)!=""]

        hroi=observed("home_flat_bet_roi_pct")
        droi=observed("draw_flat_bet_roi_pct")
        aroi=observed("away_flat_bet_roi_pct")
        oroi=observed("over25_flat_bet_roi_pct")
        uroi=observed("under25_flat_bet_roi_pct")
        hcal=observed("home_calibration_pp")
        acal=observed("away_calibration_pp")
        ocal=observed("over25_calibration_pp")

        out.append({
            "factor":key[0],"bucket":key[1],"scope_type":key[2],"scope_value":key[3],
            "seasons_with_matches":len(profiles),"total_matches":sum(matches),
            "min_season_matches":min(matches) if matches else 0,
            "max_season_matches":max(matches) if matches else 0,
            "home_roi_observed_seasons":len(hroi),
            "home_roi_positive_seasons":sum(float(p["home_flat_bet_roi_pct"])>0 for p in hroi),
            "draw_roi_observed_seasons":len(droi),
            "draw_roi_positive_seasons":sum(float(p["draw_flat_bet_roi_pct"])>0 for p in droi),
            "away_roi_observed_seasons":len(aroi),
            "away_roi_positive_seasons":sum(float(p["away_flat_bet_roi_pct"])>0 for p in aroi),
            "over25_roi_observed_seasons":len(oroi),
            "over25_roi_positive_seasons":sum(float(p["over25_flat_bet_roi_pct"])>0 for p in oroi),
            "under25_roi_observed_seasons":len(uroi),
            "under25_roi_positive_seasons":sum(float(p["under25_flat_bet_roi_pct"])>0 for p in uroi),
            "home_calibration_observed_seasons":len(hcal),
            "home_calibration_positive_seasons":sum(float(p["home_calibration_pp"])>0 for p in hcal),
            "away_calibration_observed_seasons":len(acal),
            "away_calibration_positive_seasons":sum(float(p["away_calibration_pp"])>0 for p in acal),
            "over25_calibration_observed_seasons":len(ocal),
            "over25_calibration_positive_seasons":sum(float(p["over25_calibration_pp"])>0 for p in ocal),
            "research_only":"true","operational_betting_authority":"false",
            "creates_signal":"false","promotes_factor":"false",
        })
    return out


def run(source,out_csv,stability_out,meta_out):
    rows=read_csv(source)
    joined,invalid=enrich(rows)
    profiles=aggregate(joined)
    stable=stability(joined)
    write_csv(out_csv,PROFILE_FIELDS,profiles)
    write_csv(stability_out,STABILITY_FIELDS,stable)

    meta={
        "version":VERSION,
        "generated_at_utc":now_iso(),
        "source_rows":len(rows),
        "valid_research_rows":len(joined),
        "invalid_governance_or_result_rows":invalid,
        "factor_names":FACTORS,
        "factor_profile_rows":len(profiles),
        "stability_rows":len(stable),
        "closing_1x2_matches":sum(bool(r.get("_1x2_odds")) for r in joined),
        "closing_total25_matches":sum(bool(r.get("_tot_odds")) for r in joined),
        "closing_odds_policy":"AVG_CLOSE preferred; B365_CLOSE fallback. Opening and closing odds are never mixed in one observation.",
        "market_novig_is_pbk_probability":False,
        "btts_market_baseline_available":False,
        "btts_note":"BTTS is reported as historical result rate only in this source contour; no BTTS closing-market odds are normalized here.",
        "window_reference_contract":"NEAREST_WINDOW_RELATION_GATED_V2",
        "player_level_international_status":"UNVERIFIED",
        "player_callup_inferred":False,
        "player_travel_inferred":False,
        "player_appearance_inferred":False,
        "final_tournaments_included":False,
        "non_uefa_only_windows_included":False,
        "calendar_level_only":True,
        "as_known_calendar_reference":True,
        "no_match_result_dependency":True,
        "no_lookahead":True,
        "provider_calls":0,
        "historical_backfill_only":True,
        "research_only":True,
        "operational_betting_authority":False,
        "creates_signal":False,
        "promotes_factor":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
    }
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="ops/pbk14_international_window_market_join_research.csv")
    p.add_argument("--out-csv",required=True)
    p.add_argument("--stability-out",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.out_csv,a.stability_out,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
