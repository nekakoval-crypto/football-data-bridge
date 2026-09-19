#!/usr/bin/env python3
"""Stage80 — Football-Data PBK14 historical market normalizer.

This extends the existing Top-5 Football-Data contour without changing it.

Source shapes:
- 10 "main" leagues: one CSV per league-season under mmz4281/<season>/<code>.csv;
- 4 "extra" leagues: one all-seasons CSV under new/<code>.csv.

The normalized schema intentionally reuses stage80_football_data_history.FIELDS.
For main-league rows, the existing normalizer is reused so overlapping Big-5
historical_match_id values remain stable. Extra-league rows get a deterministic
PBK14-specific ID.

This is historical research data only. It cannot create or modify probabilities,
EV/value, R1/R2/R3 eligibility, stakes, WATCH state or Forward journal entries.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.request
from pathlib import Path

try:
    import stage80_football_data_history as base
except ModuleNotFoundError:
    from scripts import stage80_football_data_history as base

VERSION = "PBK_STAGE80_FOOTBALL_DATA_PBK14_HISTORY_V1"
DEFAULT_CONFIG = Path("config/stage80_football_data_pbk14_9seasons.json")
FIELDS = list(base.FIELDS)


def load_config(path=DEFAULT_CONFIG):
    cfg=json.loads(Path(path).read_text(encoding="utf-8"))
    starts=[int(x) for x in cfg.get("season_starts") or []]
    if starts != list(range(2017,2026)):
        raise ValueError("season_starts must be exactly 2017..2025")
    leagues=cfg.get("leagues") or []
    if len(leagues)!=14:
        raise ValueError("Football-Data PBK market scope must contain exactly 14 supported leagues")
    if len(cfg.get("unsupported_pbk_leagues") or [])!=2:
        raise ValueError("exactly two locked PBK leagues must remain unsupported by this source")
    provider_ids=[int(x["provider_league_id"]) for x in leagues]
    if len(provider_ids)!=len(set(provider_ids)):
        raise ValueError("duplicate provider league ID in PBK14 source config")
    return cfg


def season_code(start):
    start=int(start)
    return f"{str(start)[2:]}{str(start+1)[2:]}"


def season_label(start):
    start=int(start)
    return f"{start}/{start+1}"


def source_specs(cfg):
    main_base=str(cfg["main_source_base"]).rstrip("/")
    extra_base=str(cfg["extra_source_base"]).rstrip("/")
    starts=[int(x) for x in cfg["season_starts"]]
    for league in cfg["leagues"]:
        mode=league["source_mode"]
        code=league["source_code"]
        if mode=="SEASON_FILE":
            for start in starts:
                sc=season_code(start)
                yield {
                    **league,
                    "season_start":start,
                    "season_code":sc,
                    "season_label":season_label(start),
                    "filename":f"{sc}_{code}.csv",
                    "url":f"{main_base}/{sc}/{code}.csv",
                }
        elif mode=="ALL_SEASONS_FILE":
            yield {
                **league,
                "season_start":None,
                "season_code":"ALL",
                "season_label":"ALL",
                "filename":f"ALL_{code}.csv",
                "url":f"{extra_base}/{code}.csv",
            }
        else:
            raise ValueError(f"unsupported source_mode: {mode}")


def fetch_specs(cfg,download_dir,timeout=40):
    root=Path(download_dir)
    root.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for spec in source_specs(cfg):
        target=root/spec["filename"]
        req=urllib.request.Request(
            spec["url"],
            headers={"User-Agent":"PBK-historical-archive/1.0"},
        )
        with urllib.request.urlopen(req,timeout=timeout) as response:
            data=response.read()
            status=getattr(response,"status",200)
        if status!=200 or not data:
            raise RuntimeError(f"download failed {status}: {spec['url']}")
        target.write_bytes(data)
        manifest.append({
            "source_code":spec["source_code"],
            "source_mode":spec["source_mode"],
            "season_start":spec["season_start"],
            "filename":spec["filename"],
            "url":spec["url"],
            "bytes":len(data),
            "sha256":hashlib.sha256(data).hexdigest(),
        })
    return manifest


def sval(row,key):
    return str((row or {}).get(key) or "").strip()


def first(row,*keys):
    for key in keys:
        value=sval(row,key)
        if value!="":
            return value
    return ""


def parse_season_start(value):
    raw=str(value or "").strip()
    if len(raw)<4:
        return None
    try:
        year=int(raw[:4])
    except ValueError:
        return None
    return year if 1900<=year<=2100 else None


def stable_extra_match_id(league,row):
    start=parse_season_start(row.get("Season"))
    parts=[
        VERSION,
        str(league["source_code"]),
        str(start or ""),
        base.parse_date(row.get("Date")),
        sval(row,"Home"),
        sval(row,"Away"),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def blank_normalized():
    return {field:"" for field in FIELDS}


def normalize_extra_row(league,row,row_number,allowed_starts):
    start=parse_season_start(row.get("Season"))
    if start not in allowed_starts:
        return None
    date_iso=base.parse_date(row.get("Date"))
    home=sval(row,"Home")
    away=sval(row,"Away")
    if not (date_iso and home and away):
        return None
    out=blank_normalized()
    out.update({
        "historical_match_id":stable_extra_match_id(league,row),
        "source":"football-data.co.uk",
        "source_url":f"{str(league['extra_source_base']).rstrip('/')}/{league['source_code']}.csv",
        "source_file":f"ALL_{league['source_code']}.csv",
        "source_season_code":sval(row,"Season"),
        "season_label":sval(row,"Season") or season_label(start),
        "league_code":league["source_code"],
        "country":league["country"],
        "league_name":league["league_name"],
        "date_iso":date_iso,
        "time_local":sval(row,"Time"),
        "home_team":home,
        "away_team":away,
        "ft_home_goals":sval(row,"HG"),
        "ft_away_goals":sval(row,"AG"),
        "ft_result":sval(row,"Res"),
        "b365_close_home":sval(row,"B365CH"),
        "b365_close_draw":sval(row,"B365CD"),
        "b365_close_away":sval(row,"B365CA"),
        "avg_close_home":first(row,"AvgCH","AvgH"),
        "avg_close_draw":first(row,"AvgCD","AvgD"),
        "avg_close_away":first(row,"AvgCA","AvgA"),
        "source_row_number":str(row_number),
        "projection_version":VERSION,
        "historical_backfill_only":"true",
        "creates_signal":"false",
        "probability_mutation":"false",
        "eligibility_mutation":"false",
        "stake_changes":"false",
        "forward_journal_mutation":"false",
    })
    return out


def read_extra(path,league,allowed_starts):
    data=Path(path).read_bytes()
    text=base.decode_csv_bytes(data)
    reader=csv.DictReader(text.splitlines())
    rows=[]
    invalid=0
    for idx,row in enumerate(reader,start=2):
        start=parse_season_start(row.get("Season"))
        if start not in allowed_starts:
            continue
        normalized=normalize_extra_row(league,row,idx,allowed_starts)
        if normalized is None:
            invalid+=1
        else:
            rows.append(normalized)
    return rows,invalid,list(reader.fieldnames or []),len(data),hashlib.sha256(data).hexdigest()


def normalize_directory(cfg,download_dir):
    root=Path(download_dir)
    allowed=set(int(x) for x in cfg["season_starts"])
    all_rows=[]
    seen=set()
    sources=[]
    invalid_total=0

    extra_base=str(cfg["extra_source_base"]).rstrip("/")
    by_code={str(x["source_code"]):dict(x,extra_source_base=extra_base) for x in cfg["leagues"]}

    for spec in source_specs(cfg):
        path=root/spec["filename"]
        if not path.exists():
            sources.append({
                "source_code":spec["source_code"],
                "source_mode":spec["source_mode"],
                "season_start":spec["season_start"],
                "filename":spec["filename"],
                "url":spec["url"],
                "present":False,
                "rows":0,
                "invalid_rows":0,
                "columns":[],
            })
            continue

        if spec["source_mode"]=="SEASON_FILE":
            raw=path.read_bytes()
            rows,invalid,columns=base.read_source_text(
                base.decode_csv_bytes(raw),
                {
                    "season_code":spec["season_code"],
                    "season_label":spec["season_label"],
                    "league_code":spec["source_code"],
                    "country":spec["country"],
                    "league_name":spec["league_name"],
                    "filename":spec["filename"],
                    "url":spec["url"],
                },
            )
            size=len(raw)
            digest=hashlib.sha256(raw).hexdigest()
        else:
            rows,invalid,columns,size,digest=read_extra(
                path,
                by_code[spec["source_code"]],
                allowed,
            )

        duplicate=0
        accepted=0
        for row in rows:
            mid=row["historical_match_id"]
            if mid in seen:
                duplicate+=1
                continue
            seen.add(mid)
            all_rows.append(row)
            accepted+=1
        invalid_total+=invalid
        sources.append({
            "source_code":spec["source_code"],
            "source_mode":spec["source_mode"],
            "season_start":spec["season_start"],
            "filename":spec["filename"],
            "url":spec["url"],
            "present":True,
            "rows":accepted,
            "invalid_rows":invalid,
            "duplicate_rows":duplicate,
            "columns":columns,
            "bytes":size,
            "sha256":digest,
        })

    all_rows.sort(key=lambda r:(
        r["date_iso"],r["league_code"],r["home_team"],r["away_team"]
    ))
    return all_rows,sources,invalid_total


def write_csv(path,rows):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def has_complete_1x2(row):
    return all(first(row,key) for key in (
        "avg_close_home","avg_close_draw","avg_close_away"
    )) or all(first(row,key) for key in (
        "b365_close_home","b365_close_draw","b365_close_away"
    ))


def has_complete_total25(row):
    return all(first(row,key) for key in (
        "avg_close_over_25","avg_close_under_25"
    )) or all(first(row,key) for key in (
        "b365_close_over_25","b365_close_under_25"
    ))


def build_meta(cfg,rows,sources,invalid,download_manifest):
    by_league={}
    by_season_start={}
    league_seasons={}
    for row in rows:
        code=row["league_code"]
        by_league[code]=by_league.get(code,0)+1
        start=parse_season_start(row["season_label"])
        if start is not None:
            by_season_start[str(start)]=by_season_start.get(str(start),0)+1
            league_seasons.setdefault(code,set()).add(start)

    supported_codes=sorted(x["source_code"] for x in cfg["leagues"])
    missing_codes=[
        code for code in supported_codes
        if not by_league.get(code)
    ]
    expected_files=sum(
        9 if x["source_mode"]=="SEASON_FILE" else 1
        for x in cfg["leagues"]
    )
    present_files=sum(1 for x in sources if x["present"])
    missing_season_cells={
        code:sorted(set(cfg["season_starts"])-set(league_seasons.get(code,set())))
        for code in supported_codes
        if set(cfg["season_starts"])-set(league_seasons.get(code,set()))
    }
    return {
        "version":VERSION,
        "scope":"Football-Data historical market coverage for 14/16 locked PBK leagues; season starts 2017..2025",
        "expected_source_files":expected_files,
        "present_source_files":present_files,
        "missing_source_files":expected_files-present_files,
        "supported_leagues":14,
        "unsupported_pbk_leagues":cfg["unsupported_pbk_leagues"],
        "normalized_matches":len(rows),
        "invalid_source_rows":invalid,
        "rows_by_league":dict(sorted(by_league.items())),
        "rows_by_season_start":dict(sorted(by_season_start.items())),
        "league_season_cells_present":sum(len(v) for v in league_seasons.values()),
        "missing_league_season_cells":missing_season_cells,
        "missing_supported_league_codes":missing_codes,
        "closing_1x2_matches":sum(has_complete_1x2(r) for r in rows),
        "closing_total25_matches":sum(has_complete_total25(r) for r in rows),
        "sources":sources,
        "download_manifest":download_manifest,
        "historical_backfill_only":True,
        "forward_validation_input":False,
        "research_only":True,
        "operational_betting_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
    }


def run(config_path,download_dir,out_csv,meta_out,fetch=False):
    cfg=load_config(config_path)
    manifest=fetch_specs(cfg,download_dir) if fetch else []
    rows,sources,invalid=normalize_directory(cfg,download_dir)
    write_csv(out_csv,rows)
    meta=build_meta(cfg,rows,sources,invalid,manifest)
    Path(meta_out).write_text(
        json.dumps(meta,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default=str(DEFAULT_CONFIG))
    p.add_argument("--download-dir",required=True)
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    p.add_argument("--fetch",action="store_true")
    a=p.parse_args()
    print(json.dumps(
        run(a.config,a.download_dir,a.out_csv,a.meta_out,a.fetch),
        ensure_ascii=False,
    ))


if __name__=="__main__":
    main()
