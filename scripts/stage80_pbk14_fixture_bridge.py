#!/usr/bin/env python3
"""Stage80 — conservative PBK14 Football-Data -> API-Football fixture bridge.

No fuzzy string matching is used.

Team identity evidence, in order:
1. AUTO: exact conservative canonical team name within league-season.
2. HIGH: unique full source schedule fingerprint contained in one provider team
   fingerprint. Fingerprints use (date, home/away side, goals-for, goals-against)
   and require at least five source matches. Final scores are used ONLY for
   historical identity resolution, never as a prematch feature.

Fixture identity then requires:
- same provider league;
- same season start;
- exact calendar date;
- mapped home and away provider team IDs;
- exact final score;
- unique provider fixture candidate.

Only AUTO/HIGH rows are eligible for downstream historical research joins.
REVIEW/UNMAPPED remain excluded.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_PBK14_FIXTURE_BRIDGE_V1"
FINAL={"FT","AET","PEN"}
FIELDS=[
    "historical_match_id","league_code","provider_league_id","season_start","date_iso",
    "source_home_team","source_away_team","source_home_goals","source_away_goals",
    "api_fixture_id","api_kickoff_utc","api_home_team_id","api_home_team",
    "api_away_team_id","api_away_team","api_home_goals","api_away_goals",
    "home_team_map_status","away_team_map_status","mapping_status","mapping_reason",
    "exact_date_required","final_score_identity_evidence","fuzzy_string_matching_used",
    "one_to_one_verified","historical_backfill_only","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
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


def parse_season_start(value):
    raw=sval(value)
    if len(raw)<4:
        return None
    try:
        year=int(raw[:4])
    except ValueError:
        return None
    return year if 1900<=year<=2100 else None


def kickoff_day(value):
    raw=sval(value)
    if not raw:
        return ""
    try:
        dt=datetime.fromisoformat(raw.replace("Z","+00:00"))
        if dt.tzinfo is None:
            return ""
        return dt.astimezone(timezone.utc).date().isoformat()
    except ValueError:
        return ""


def canonical_name(value):
    text=unicodedata.normalize("NFKD",sval(value))
    text="".join(ch for ch in text if not unicodedata.combining(ch))
    text=text.casefold().replace("&"," and ")
    text=re.sub(r"[^a-z0-9]+"," ",text)
    return " ".join(text.split())


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path,rows):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def load_config(path):
    cfg=json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        str(x["source_code"]):{
            "provider_league_id":int(x["provider_league_id"]),
            "country":x["country"],
            "league_name":x["league_name"],
        }
        for x in cfg.get("leagues") or []
    }


def source_event(row,side):
    hg=as_int(row.get("ft_home_goals"))
    ag=as_int(row.get("ft_away_goals"))
    if hg is None or ag is None:
        return None
    if side=="H":
        return (sval(row.get("date_iso")),"H",hg,ag)
    return (sval(row.get("date_iso")),"A",ag,hg)


def provider_event(row,side):
    hg=as_int(row.get("home_goals"))
    ag=as_int(row.get("away_goals"))
    day=kickoff_day(row.get("kickoff_utc"))
    if hg is None or ag is None or not day:
        return None
    if side=="H":
        return (day,"H",hg,ag)
    return (day,"A",ag,hg)


def scope_rows(source_rows,api_rows,league_code,provider_id,season_start):
    src=[
        r for r in source_rows
        if sval(r.get("league_code"))==league_code
        and parse_season_start(r.get("season_label"))==season_start
    ]
    api=[
        r for r in api_rows
        if sval(r.get("competition_role"))=="DOMESTIC_LEAGUE"
        and as_int(r.get("provider_competition_id"))==provider_id
        and as_int(r.get("season"))==season_start
        and sval(r.get("status")) in FINAL
    ]
    return src,api


def team_maps(src,api):
    source_names=sorted({
        sval(r.get(k)) for r in src for k in ("home_team","away_team") if sval(r.get(k))
    })
    provider_by_id={}
    for row in api:
        provider_by_id[sval(row.get("home_team_id"))]=sval(row.get("home_team"))
        provider_by_id[sval(row.get("away_team_id"))]=sval(row.get("away_team"))
    provider_ids=sorted(x for x in provider_by_id if x)

    provider_by_canon=defaultdict(list)
    for tid in provider_ids:
        provider_by_canon[canonical_name(provider_by_id[tid])].append(tid)

    mapped={}
    used_provider=set()
    for name in source_names:
        hits=provider_by_canon.get(canonical_name(name),[])
        if len(hits)==1:
            mapped[name]=(hits[0],"AUTO","CANONICAL_EXACT")
            used_provider.add(hits[0])

    source_fp=defaultdict(set)
    for row in src:
        h=sval(row.get("home_team")); a=sval(row.get("away_team"))
        he=source_event(row,"H"); ae=source_event(row,"A")
        if h and he: source_fp[h].add(he)
        if a and ae: source_fp[a].add(ae)

    provider_fp=defaultdict(set)
    for row in api:
        h=sval(row.get("home_team_id")); a=sval(row.get("away_team_id"))
        he=provider_event(row,"H"); ae=provider_event(row,"A")
        if h and he: provider_fp[h].add(he)
        if a and ae: provider_fp[a].add(ae)

    unresolved=[name for name in source_names if name not in mapped]
    for name in unresolved:
        fp=source_fp.get(name,set())
        if len(fp)<5:
            continue
        candidates=[]
        for tid in provider_ids:
            if tid in used_provider:
                continue
            pfp=provider_fp.get(tid,set())
            if fp and fp.issubset(pfp):
                candidates.append(tid)
        if len(candidates)==1:
            tid=candidates[0]
            mapped[name]=(tid,"HIGH","SCHEDULE_SCORE_FINGERPRINT")
            used_provider.add(tid)

    return mapped,provider_by_id


def map_scope(src,api,league_code,provider_id,season_start):
    teams,provider_names=team_maps(src,api)
    by_key=defaultdict(list)
    for row in api:
        key=(
            kickoff_day(row.get("kickoff_utc")),
            sval(row.get("home_team_id")),
            sval(row.get("away_team_id")),
        )
        by_key[key].append(row)

    out=[]
    for row in src:
        home=sval(row.get("home_team")); away=sval(row.get("away_team"))
        hmap=teams.get(home); amap=teams.get(away)
        base={
            "historical_match_id":sval(row.get("historical_match_id")),
            "league_code":league_code,
            "provider_league_id":provider_id,
            "season_start":season_start,
            "date_iso":sval(row.get("date_iso")),
            "source_home_team":home,
            "source_away_team":away,
            "source_home_goals":sval(row.get("ft_home_goals")),
            "source_away_goals":sval(row.get("ft_away_goals")),
            "api_fixture_id":"",
            "api_kickoff_utc":"",
            "api_home_team_id":hmap[0] if hmap else "",
            "api_home_team":provider_names.get(hmap[0],"") if hmap else "",
            "api_away_team_id":amap[0] if amap else "",
            "api_away_team":provider_names.get(amap[0],"") if amap else "",
            "api_home_goals":"",
            "api_away_goals":"",
            "home_team_map_status":hmap[1] if hmap else "UNMAPPED",
            "away_team_map_status":amap[1] if amap else "UNMAPPED",
            "mapping_status":"UNMAPPED",
            "mapping_reason":"TEAM_IDENTITY_INCOMPLETE",
            "exact_date_required":"true",
            "final_score_identity_evidence":"true",
            "fuzzy_string_matching_used":"false",
            "one_to_one_verified":"false",
            "historical_backfill_only":"true",
            "research_only":"true",
            "operational_betting_authority":"false",
            "creates_signal":"false",
            "probability_mutation":"false",
            "eligibility_mutation":"false",
            "stake_changes":"false",
            "forward_journal_mutation":"false",
        }
        if hmap and amap:
            candidates=by_key.get((base["date_iso"],hmap[0],amap[0]),[])
            sh=as_int(row.get("ft_home_goals")); sa=as_int(row.get("ft_away_goals"))
            score_matches=[
                x for x in candidates
                if as_int(x.get("home_goals"))==sh and as_int(x.get("away_goals"))==sa
            ]
            if len(score_matches)==1:
                api_row=score_matches[0]
                status="AUTO" if hmap[1]=="AUTO" and amap[1]=="AUTO" else "HIGH"
                base.update({
                    "api_fixture_id":sval(api_row.get("fixture_id")),
                    "api_kickoff_utc":sval(api_row.get("kickoff_utc")),
                    "api_home_goals":sval(api_row.get("home_goals")),
                    "api_away_goals":sval(api_row.get("away_goals")),
                    "mapping_status":status,
                    "mapping_reason":"EXACT_DATE_TEAMS_SCORE_UNIQUE",
                    "one_to_one_verified":"true",
                })
            elif len(score_matches)>1:
                base["mapping_status"]="REVIEW"
                base["mapping_reason"]="MULTIPLE_PROVIDER_FIXTURES_SAME_DATE_TEAMS_SCORE"
            elif candidates:
                base["mapping_status"]="REVIEW"
                base["mapping_reason"]="DATE_TEAMS_MATCH_BUT_SCORE_MISMATCH"
            else:
                base["mapping_status"]="REVIEW"
                base["mapping_reason"]="MAPPED_TEAMS_BUT_NO_EXACT_DATE_FIXTURE"
        out.append(base)

    fixture_counts=Counter(
        r["api_fixture_id"] for r in out
        if r["mapping_status"] in {"AUTO","HIGH"} and r["api_fixture_id"]
    )
    conflicts={fid for fid,n in fixture_counts.items() if n>1}
    if conflicts:
        for row in out:
            if row["api_fixture_id"] in conflicts:
                row["mapping_status"]="REVIEW"
                row["mapping_reason"]="ONE_TO_ONE_PROVIDER_FIXTURE_CONFLICT"
                row["one_to_one_verified"]="false"
    return out


def bridge(source_rows,api_rows,league_map):
    rows=[]
    scopes=[]
    for code,info in sorted(league_map.items()):
        for season_start in range(2017,2026):
            src,api=scope_rows(
                source_rows,api_rows,code,info["provider_league_id"],season_start
            )
            if not src:
                scopes.append({
                    "league_code":code,"season_start":season_start,
                    "source_rows":0,"provider_rows":len(api),
                    "mapped_auto":0,"mapped_high":0,"review":0,"unmapped":0,
                })
                continue
            mapped=map_scope(
                src,api,code,info["provider_league_id"],season_start
            )
            rows.extend(mapped)
            counts=Counter(r["mapping_status"] for r in mapped)
            scopes.append({
                "league_code":code,"season_start":season_start,
                "source_rows":len(src),"provider_rows":len(api),
                "mapped_auto":counts.get("AUTO",0),
                "mapped_high":counts.get("HIGH",0),
                "review":counts.get("REVIEW",0),
                "unmapped":counts.get("UNMAPPED",0),
            })
    rows.sort(key=lambda r:(
        r["date_iso"],r["league_code"],r["source_home_team"],r["source_away_team"]
    ))
    return rows,scopes


def build_meta(rows,scopes):
    counts=Counter(r["mapping_status"] for r in rows)
    mapped=[r for r in rows if r["mapping_status"] in {"AUTO","HIGH"}]
    fixture_ids=[r["api_fixture_id"] for r in mapped if r["api_fixture_id"]]
    by_league=defaultdict(Counter)
    for row in rows:
        by_league[row["league_code"]][row["mapping_status"]]+=1
    return {
        "version":VERSION,
        "generated_at_utc":iso_now(),
        "source_rows":len(rows),
        "mapped_auto":counts.get("AUTO",0),
        "mapped_high":counts.get("HIGH",0),
        "mapped_auto_high":len(mapped),
        "review":counts.get("REVIEW",0),
        "unmapped":counts.get("UNMAPPED",0),
        "mapped_pct":round(100.0*len(mapped)/len(rows),3) if rows else 0.0,
        "unique_mapped_api_fixture_ids":len(set(fixture_ids)),
        "duplicate_mapped_api_fixture_ids":len(fixture_ids)-len(set(fixture_ids)),
        "league_season_scopes":scopes,
        "mapping_by_league":{
            code:dict(sorted(counter.items()))
            for code,counter in sorted(by_league.items())
        },
        "mapping_policy":{
            "fuzzy_string_matching_used":False,
            "auto":"unique conservative canonical-name mapping + exact date/teams/final score",
            "high":"unique schedule+score team fingerprint + exact date/teams/final score",
            "review_unmapped_excluded":True,
            "final_score_identity_only":True,
        },
        "historical_backfill_only":True,
        "research_only":True,
        "operational_betting_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
    }


def run(source,api_archive,config,out_csv,meta_out):
    source_rows=read_csv(source)
    api_rows=read_csv(api_archive)
    league_map=load_config(config)
    rows,scopes=bridge(source_rows,api_rows,league_map)
    write_csv(out_csv,rows)
    meta=build_meta(rows,scopes)
    Path(meta_out).write_text(
        json.dumps(meta,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--api-archive",default="ops/pbk16_all_competition_fixture_history.csv")
    p.add_argument("--config",default="config/stage80_football_data_pbk14_9seasons.json")
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(
        run(a.source,a.api_archive,a.config,a.out_csv,a.meta_out),
        ensure_ascii=False,
    ))


if __name__=="__main__":
    main()
