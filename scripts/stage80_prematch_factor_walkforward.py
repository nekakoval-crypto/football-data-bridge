#!/usr/bin/env python3
"""Stage80 — walk-forward validation research for no-lookahead prematch factors.

For each factor bucket, scope and market target, each test season is evaluated
using only strictly earlier seasons as the training window. Historical closing
market no-vig probabilities are benchmark baselines, never PBK probabilities.

This layer records stability evidence only. It does not rank/promote factors and
cannot mutate probability, EV/value, eligibility, stake or Forward state.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from stage80_prematch_factor_research import enrich, factor_buckets
except ImportError:  # pragma: no cover - package import in unit tests
    from scripts.stage80_prematch_factor_research import enrich, factor_buckets

VERSION = "PBK_STAGE80_PREMATCH_FACTOR_WALKFORWARD_V1"
TARGETS = ("HOME", "DRAW", "AWAY", "OVER25", "UNDER25")
MIN_PRIOR_SEASONS = 2
MIN_TRAIN_MARKET_MATCHES = 100
MIN_TEST_MARKET_MATCHES = 30
CALIBRATION_NEUTRAL_EPS_PP = 0.25
ROI_NEUTRAL_EPS_PCT = 0.25

FOLD_FIELDS = [
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
    "probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation",
]

SUMMARY_FIELDS = [
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


def season_start(label):
    try:
        return int(str(label).split("/",1)[0])
    except (TypeError,ValueError):
        return None


def avg(values):
    vals=[float(v) for v in values if v is not None]
    return None if not vals else sum(vals)/len(vals)


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
    if value > epsilon:
        return "POSITIVE"
    if value < -epsilon:
        return "NEGATIVE"
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
    obs=[item for item in obs if item is not None]
    if not obs:
        return {
            "matches":0,"hit_rate":None,"market_novig":None,
            "calibration_pp":None,"roi_pct":None,
        }
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
        {str(row.get("season_label") or "").strip() for row in joined if season_start(row.get("season_label")) is not None},
        key=season_start,
    )
    rows=[]
    for (factor,bucket,scope_type,scope_value),items in sorted(groups.items()):
        for test_season in all_seasons:
            test_start=season_start(test_season)
            prior=[s for s in all_seasons if season_start(s) < test_start]
            if len(prior) < MIN_PRIOR_SEASONS:
                continue
            train=[r for r in items if season_start(r.get("season_label")) is not None and season_start(r.get("season_label")) < test_start]
            test=[r for r in items if str(r.get("season_label") or "").strip()==test_season]
            if not test:
                continue
            train_seasons=sorted(
                {str(r.get("season_label") or "").strip() for r in train},
                key=season_start,
            )
            if len(train_seasons) < MIN_PRIOR_SEASONS:
                continue

            for target in TARGETS:
                tr=target_metrics(train,target); te=target_metrics(test,target)
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
                rows.append({
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
                    "creates_signal":"false","probability_mutation":"false",
                    "eligibility_mutation":"false","stake_changes":"false",
                    "forward_journal_mutation":"false",
                })
    return rows


def summarize_folds(folds):
    groups=defaultdict(list)
    for row in folds:
        key=(row["factor"],row["bucket"],row["scope_type"],row["scope_value"],row["target"])
        groups[key].append(row)
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
            "calibration_sign_persistence_rate":rounded(
                cal_persist/len(cal_non_neutral) if cal_non_neutral else None,5
            ),
            "roi_non_neutral_eligible_folds":len(roi_non_neutral),
            "roi_sign_persistent_folds":roi_persist,
            "roi_sign_persistence_rate":rounded(
                roi_persist/len(roi_non_neutral) if roi_non_neutral else None,5
            ),
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


def run(matches_path,context_path,folds_out,summary_out,meta_out):
    matches=read_csv(matches_path); contexts=read_csv(context_path)
    joined,diag=enrich(matches,contexts)
    folds=build_folds(joined)
    summary=summarize_folds(folds)
    eligible=sum(r["sample_threshold_pass"]=="true" for r in folds)
    seasons=sorted(
        {str(r.get("season_label") or "").strip() for r in joined if season_start(r.get("season_label")) is not None},
        key=season_start,
    )
    status="OK" if (
        diag["source_rows"]==16111
        and diag["context_rows"]==16111
        and diag["joined_rows"]==16111
        and diag["invalid_context_governance_rows"]==0
        and diag["source_without_context"]==0
        and diag["context_without_source"]==0
        and len(seasons)==9
        and len(folds)>0
        and len(summary)>0
        and eligible>0
    ) else "ATTENTION"
    meta={
        "version":VERSION,"generated_at_utc":iso_now(),"status":status,
        **diag,
        "season_labels":seasons,
        "targets":list(TARGETS),
        "fold_rows":len(folds),"summary_rows":len(summary),
        "sample_threshold_pass_folds":eligible,
        "min_prior_seasons":MIN_PRIOR_SEASONS,
        "min_train_market_matches":MIN_TRAIN_MARKET_MATCHES,
        "min_test_market_matches":MIN_TEST_MARKET_MATCHES,
        "calibration_neutral_epsilon_pp":CALIBRATION_NEUTRAL_EPS_PP,
        "roi_neutral_epsilon_pct":ROI_NEUTRAL_EPS_PCT,
        "validation_semantics":"Each test season uses only strictly earlier seasons as its training window. Sign-persistence is descriptive research evidence, not model promotion.",
        "market_probability_semantics":"Historical closing-market no-vig is a benchmark only and is not PBK probability.",
        "research_only":True,"operational_betting_authority":False,
        "creates_signal":False,"promotes_factor":False,
        "probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
        "provider_calls":0,
    }
    write_csv(folds_out,FOLD_FIELDS,folds)
    write_csv(summary_out,SUMMARY_FIELDS,summary)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--matches",required=True)
    p.add_argument("--context",required=True)
    p.add_argument("--folds-out",required=True)
    p.add_argument("--summary-out",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.matches,a.context,a.folds_out,a.summary_out,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
