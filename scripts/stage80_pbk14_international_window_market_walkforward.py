#!/usr/bin/env python3
"""Stage80 — walk-forward validation for PBK14 international-window factors.

Each test season is evaluated only against strictly earlier seasons. Input is the
durable AUTO/HIGH PBK14 historical market × PBK16 international-window V2 join.

Historical closing-market no-vig probabilities are benchmark baselines only and
never PBK probabilities. This layer records persistence evidence and never
ranks/selects/promotes factors or mutates any betting/model authority.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from stage80_pbk14_international_window_market_research import enrich, factor_buckets
except ImportError:  # pragma: no cover
    from scripts.stage80_pbk14_international_window_market_research import enrich, factor_buckets

VERSION="PBK_STAGE80_PBK14_INTERNATIONAL_WINDOW_MARKET_WALKFORWARD_V1"
TARGETS=("HOME","DRAW","AWAY","OVER25","UNDER25")
MIN_PRIOR_SEASONS=2
MIN_TRAIN_MARKET_MATCHES=100
MIN_TEST_MARKET_MATCHES=30
CALIBRATION_NEUTRAL_EPS_PP=0.25
ROI_NEUTRAL_EPS_PCT=0.25

FOLD_FIELDS=[
    "factor","bucket","scope_type","scope_value","target",
    "test_season","train_first_season","train_last_season","train_seasons",
    "train_market_matches","test_market_matches","sample_threshold_pass",
    "train_hit_rate","test_hit_rate",
    "train_avg_market_novig","test_avg_market_novig",
    "train_calibration_pp","test_calibration_pp",
    "train_flat_bet_roi_pct","test_flat_bet_roi_pct",
    "train_calibration_sign","test_calibration_sign","calibration_sign_persists",
    "train_roi_sign","test_roi_sign","roi_sign_persists",
    "research_only","operational_betting_authority","creates_signal",
    "promotes_factor","probability_mutation","eligibility_mutation",
    "stake_changes","forward_journal_mutation",
]

SUMMARY_FIELDS=[
    "factor","bucket","scope_type","scope_value","target",
    "folds","sample_threshold_pass_folds","total_train_market_matches",
    "total_test_market_matches","first_test_season","last_test_season",
    "calibration_non_neutral_eligible_folds","calibration_sign_persistent_folds",
    "calibration_sign_persistence_rate",
    "roi_non_neutral_eligible_folds","roi_sign_persistent_folds",
    "roi_sign_persistence_rate",
    "weighted_test_calibration_pp","weighted_test_flat_bet_roi_pct",
    "positive_test_calibration_folds","positive_test_roi_folds",
    "research_only","operational_betting_authority","creates_signal",
    "promotes_factor","probability_mutation","eligibility_mutation",
    "stake_changes","forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


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


def season_start(value):
    raw=str(value or "").strip()
    try:
        return int(raw[:4])
    except (TypeError,ValueError):
        return None


def weighted_avg(pairs):
    pairs=[(float(v),int(w)) for v,w in pairs if v is not None and int(w)>0]
    den=sum(w for _,w in pairs)
    return None if not den else sum(v*w for v,w in pairs)/den


def rounded(value,digits=4):
    return "" if value is None else round(float(value),digits)


def sign(value,epsilon):
    if value is None:
        return "UNKNOWN"
    value=float(value)
    if value>epsilon: return "POSITIVE"
    if value<-epsilon: return "NEGATIVE"
    return "NEUTRAL"


def bool_text(value):
    if value is None:
        return ""
    return "true" if value else "false"


def target_observation(row,target):
    if target in {"HOME","DRAW","AWAY"}:
        odds=row.get("_1x2_odds"); probs=row.get("_1x2_novig")
        if not odds or not probs:
            return None
        idx={"HOME":0,"DRAW":1,"AWAY":2}[target]
        hit=row.get("_result")=={"HOME":"H","DRAW":"D","AWAY":"A"}[target]
        return bool(hit),float(odds[idx]),float(probs[idx])

    odds=row.get("_tot_odds"); probs=row.get("_tot_novig")
    if not odds or not probs:
        return None
    idx=0 if target=="OVER25" else 1
    hit=bool(row.get("_over25")) if target=="OVER25" else not bool(row.get("_over25"))
    return bool(hit),float(odds[idx]),float(probs[idx])


def target_metrics(rows,target):
    obs=[target_observation(row,target) for row in rows]
    obs=[x for x in obs if x is not None]
    if not obs:
        return {"matches":0,"hit_rate":None,"market_novig":None,"calibration_pp":None,"roi_pct":None}
    hits=sum(hit for hit,_,__ in obs)
    hit_rate=hits/len(obs)
    market=sum(prob for _,__,prob in obs)/len(obs)
    returns=[odds-1.0 if hit else -1.0 for hit,odds,_ in obs]
    return {
        "matches":len(obs),
        "hit_rate":hit_rate,
        "market_novig":market,
        "calibration_pp":100.0*(hit_rate-market),
        "roi_pct":100.0*sum(returns)/len(returns),
    }


def grouped_rows(joined):
    groups=defaultdict(list)
    for row in joined:
        league=str(row.get("league_code") or "").strip()
        for factor,bucket in factor_buckets(row).items():
            groups[(factor,bucket,"ALL","ALL")].append(row)
            if league:
                groups[(factor,bucket,"LEAGUE",league)].append(row)
    return groups


def build_folds(joined):
    groups=grouped_rows(joined)
    all_seasons=sorted(
        {str(row.get("season_start") or "").strip() for row in joined if season_start(row.get("season_start")) is not None},
        key=season_start,
    )
    folds=[]
    for (factor,bucket,scope_type,scope_value),items in sorted(groups.items()):
        for test_season in all_seasons:
            test_start=season_start(test_season)
            prior=[s for s in all_seasons if season_start(s)<test_start]
            if len(prior)<MIN_PRIOR_SEASONS:
                continue

            train=[r for r in items if season_start(r.get("season_start")) is not None and season_start(r.get("season_start"))<test_start]
            test=[r for r in items if str(r.get("season_start") or "").strip()==test_season]
            if not test:
                continue
            train_seasons=sorted(
                {str(r.get("season_start") or "").strip() for r in train},
                key=season_start,
            )
            if len(train_seasons)<MIN_PRIOR_SEASONS:
                continue

            for target in TARGETS:
                tr=target_metrics(train,target)
                te=target_metrics(test,target)
                sample_ok=(
                    len(train_seasons)>=MIN_PRIOR_SEASONS
                    and tr["matches"]>=MIN_TRAIN_MARKET_MATCHES
                    and te["matches"]>=MIN_TEST_MARKET_MATCHES
                )
                tr_cal_sign=sign(tr["calibration_pp"],CALIBRATION_NEUTRAL_EPS_PP)
                te_cal_sign=sign(te["calibration_pp"],CALIBRATION_NEUTRAL_EPS_PP)
                tr_roi_sign=sign(tr["roi_pct"],ROI_NEUTRAL_EPS_PCT)
                te_roi_sign=sign(te["roi_pct"],ROI_NEUTRAL_EPS_PCT)
                cal_persist=(
                    sample_ok and tr_cal_sign in {"POSITIVE","NEGATIVE"}
                    and te_cal_sign==tr_cal_sign
                )
                roi_persist=(
                    sample_ok and tr_roi_sign in {"POSITIVE","NEGATIVE"}
                    and te_roi_sign==tr_roi_sign
                )
                folds.append({
                    "factor":factor,"bucket":bucket,"scope_type":scope_type,"scope_value":scope_value,
                    "target":target,"test_season":test_season,
                    "train_first_season":train_seasons[0],
                    "train_last_season":train_seasons[-1],
                    "train_seasons":len(train_seasons),
                    "train_market_matches":tr["matches"],"test_market_matches":te["matches"],
                    "sample_threshold_pass":bool_text(sample_ok),
                    "train_hit_rate":rounded(tr["hit_rate"],5),"test_hit_rate":rounded(te["hit_rate"],5),
                    "train_avg_market_novig":rounded(tr["market_novig"],5),
                    "test_avg_market_novig":rounded(te["market_novig"],5),
                    "train_calibration_pp":rounded(tr["calibration_pp"],3),
                    "test_calibration_pp":rounded(te["calibration_pp"],3),
                    "train_flat_bet_roi_pct":rounded(tr["roi_pct"],3),
                    "test_flat_bet_roi_pct":rounded(te["roi_pct"],3),
                    "train_calibration_sign":tr_cal_sign,"test_calibration_sign":te_cal_sign,
                    "calibration_sign_persists":bool_text(cal_persist) if sample_ok else "",
                    "train_roi_sign":tr_roi_sign,"test_roi_sign":te_roi_sign,
                    "roi_sign_persists":bool_text(roi_persist) if sample_ok else "",
                    "research_only":"true","operational_betting_authority":"false",
                    "creates_signal":"false","promotes_factor":"false",
                    "probability_mutation":"false","eligibility_mutation":"false",
                    "stake_changes":"false","forward_journal_mutation":"false",
                })
    return folds


def summarize_folds(folds):
    groups=defaultdict(list)
    for row in folds:
        groups[(row["factor"],row["bucket"],row["scope_type"],row["scope_value"],row["target"])].append(row)

    out=[]
    for key,items in sorted(groups.items()):
        eligible=[r for r in items if r["sample_threshold_pass"]=="true"]
        cal_non_neutral=[r for r in eligible if r["train_calibration_sign"] in {"POSITIVE","NEGATIVE"}]
        roi_non_neutral=[r for r in eligible if r["train_roi_sign"] in {"POSITIVE","NEGATIVE"}]
        cal_persist=sum(r["calibration_sign_persists"]=="true" for r in cal_non_neutral)
        roi_persist=sum(r["roi_sign_persists"]=="true" for r in roi_non_neutral)
        out.append({
            "factor":key[0],"bucket":key[1],"scope_type":key[2],"scope_value":key[3],"target":key[4],
            "folds":len(items),"sample_threshold_pass_folds":len(eligible),
            "total_train_market_matches":sum(int(r["train_market_matches"]) for r in items),
            "total_test_market_matches":sum(int(r["test_market_matches"]) for r in items),
            "first_test_season":min((r["test_season"] for r in items),key=season_start),
            "last_test_season":max((r["test_season"] for r in items),key=season_start),
            "calibration_non_neutral_eligible_folds":len(cal_non_neutral),
            "calibration_sign_persistent_folds":cal_persist,
            "calibration_sign_persistence_rate":rounded(cal_persist/len(cal_non_neutral) if cal_non_neutral else None,5),
            "roi_non_neutral_eligible_folds":len(roi_non_neutral),
            "roi_sign_persistent_folds":roi_persist,
            "roi_sign_persistence_rate":rounded(roi_persist/len(roi_non_neutral) if roi_non_neutral else None,5),
            "weighted_test_calibration_pp":rounded(weighted_avg([
                (float(r["test_calibration_pp"]),int(r["test_market_matches"]))
                for r in eligible if r["test_calibration_pp"]!=""
            ]),3),
            "weighted_test_flat_bet_roi_pct":rounded(weighted_avg([
                (float(r["test_flat_bet_roi_pct"]),int(r["test_market_matches"]))
                for r in eligible if r["test_flat_bet_roi_pct"]!=""
            ]),3),
            "positive_test_calibration_folds":sum(
                r["test_calibration_pp"]!="" and float(r["test_calibration_pp"])>CALIBRATION_NEUTRAL_EPS_PP
                for r in eligible
            ),
            "positive_test_roi_folds":sum(
                r["test_flat_bet_roi_pct"]!="" and float(r["test_flat_bet_roi_pct"])>ROI_NEUTRAL_EPS_PCT
                for r in eligible
            ),
            "research_only":"true","operational_betting_authority":"false",
            "creates_signal":"false","promotes_factor":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        })
    return out


def run(source,folds_out,summary_out,meta_out):
    rows=read_csv(source)
    joined,invalid=enrich(rows)
    folds=build_folds(joined)
    summary=summarize_folds(folds)
    eligible=sum(r["sample_threshold_pass"]=="true" for r in folds)
    seasons=sorted(
        {str(r.get("season_start") or "").strip() for r in joined if season_start(r.get("season_start")) is not None},
        key=season_start,
    )
    status="OK" if (
        len(rows)>0
        and len(joined)==len(rows)
        and invalid==0
        and len(seasons)==9
        and folds
        and summary
        and eligible>0
    ) else "ATTENTION"

    meta={
        "version":VERSION,
        "generated_at_utc":iso_now(),
        "status":status,
        "source_rows":len(rows),
        "valid_research_rows":len(joined),
        "invalid_governance_or_result_rows":invalid,
        "season_starts":seasons,
        "factor_names":sorted({f for r in joined for f in factor_buckets(r)}),
        "targets":list(TARGETS),
        "fold_rows":len(folds),
        "summary_rows":len(summary),
        "sample_threshold_pass_folds":eligible,
        "min_prior_seasons":MIN_PRIOR_SEASONS,
        "min_train_market_matches":MIN_TRAIN_MARKET_MATCHES,
        "min_test_market_matches":MIN_TEST_MARKET_MATCHES,
        "calibration_neutral_epsilon_pp":CALIBRATION_NEUTRAL_EPS_PP,
        "roi_neutral_epsilon_pct":ROI_NEUTRAL_EPS_PCT,
        "validation_semantics":"Each test season uses only strictly earlier seasons. Sign persistence is research evidence only and never factor promotion.",
        "market_probability_semantics":"Historical closing-market no-vig is a benchmark only and is not PBK probability.",
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
        "research_only":True,
        "operational_betting_authority":False,
        "creates_signal":False,
        "promotes_factor":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
    }
    write_csv(folds_out,FOLD_FIELDS,folds)
    write_csv(summary_out,SUMMARY_FIELDS,summary)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="ops/pbk14_international_window_market_join_research.csv")
    p.add_argument("--folds-out",required=True)
    p.add_argument("--summary-out",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.folds_out,a.summary_out,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
