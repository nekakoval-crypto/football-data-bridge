#!/usr/bin/env python3
"""Stage80 — Football-Data.co.uk Top-5 nine-season historical source normalizer.

This is a historical enrichment/backfill source layer, not operational current
truth and not forward-validation evidence. It can download the configured public
CSV files or normalize an already-downloaded directory.

The output preserves provenance per row and a conservative stable subset of
results, match stats, and bookmaker/market columns when present. Missing source
columns remain empty/unknown rather than zero-filled.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VERSION = "PBK_STAGE80_FOOTBALL_DATA_HISTORY_V1"

FIELDS = [
    "historical_match_id","source","source_url","source_file","source_season_code",
    "season_label","league_code","country","league_name","date_iso","time_local","referee",
    "home_team","away_team","ft_home_goals","ft_away_goals","ft_result",
    "ht_home_goals","ht_away_goals","ht_result",
    "home_shots","away_shots","home_shots_on_target","away_shots_on_target",
    "home_fouls","away_fouls","home_corners","away_corners",
    "home_yellows","away_yellows","home_reds","away_reds",
    "b365_home","b365_draw","b365_away","avg_home","avg_draw","avg_away",
    "b365_close_home","b365_close_draw","b365_close_away","avg_close_home","avg_close_draw","avg_close_away",
    "b365_over_25","b365_under_25","avg_over_25","avg_under_25",
    "b365_close_over_25","b365_close_under_25","avg_close_over_25","avg_close_under_25",
    "asian_handicap_line","b365_ah_home","b365_ah_away","avg_ah_home","avg_ah_away",
    "asian_handicap_close_line","b365_close_ah_home","b365_close_ah_away","avg_close_ah_home","avg_close_ah_away",
    "source_row_number","projection_version","historical_backfill_only",
    "creates_signal","probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_specs(config):
    base=str(config["source_base"]).rstrip("/")
    for season in config["seasons"]:
        for league in config["leagues"]:
            filename=f"{season['code']}_{league['code']}.csv"
            yield {
                "season_code":season["code"],"season_label":season["label"],
                "league_code":league["code"],"country":league["country"],
                "league_name":league["league_name"],"filename":filename,
                "url":f"{base}/{season['code']}/{league['code']}.csv",
            }


def decode_csv_bytes(data):
    for enc in ("utf-8-sig","cp1252","latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8",errors="replace")


def parse_date(value):
    raw=str(value or "").strip()
    for fmt in ("%d/%m/%Y","%d/%m/%y","%d-%m-%Y","%d-%m-%y"):
        try:
            return datetime.strptime(raw,fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def sval(row,key):
    return str((row or {}).get(key) or "").strip()


def first(row,*keys):
    for key in keys:
        value=sval(row,key)
        if value!="":
            return value
    return ""


def stable_match_id(spec,row):
    parts=[
        VERSION,spec["season_code"],spec["league_code"],parse_date(row.get("Date")),
        sval(row,"HomeTeam"),sval(row,"AwayTeam"),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def normalize_row(spec,row,row_number):
    home=sval(row,"HomeTeam"); away=sval(row,"AwayTeam")
    date_iso=parse_date(row.get("Date"))
    if not home or not away or not date_iso:
        return None
    return {
        "historical_match_id":stable_match_id(spec,row),
        "source":"football-data.co.uk",
        "source_url":spec["url"],
        "source_file":spec["filename"],
        "source_season_code":spec["season_code"],
        "season_label":spec["season_label"],
        "league_code":spec["league_code"],
        "country":spec["country"],
        "league_name":spec["league_name"],
        "date_iso":date_iso,
        "time_local":sval(row,"Time"),
        "referee":sval(row,"Referee"),
        "home_team":home,
        "away_team":away,
        "ft_home_goals":sval(row,"FTHG"),
        "ft_away_goals":sval(row,"FTAG"),
        "ft_result":sval(row,"FTR"),
        "ht_home_goals":sval(row,"HTHG"),
        "ht_away_goals":sval(row,"HTAG"),
        "ht_result":sval(row,"HTR"),
        "home_shots":sval(row,"HS"),
        "away_shots":sval(row,"AS"),
        "home_shots_on_target":sval(row,"HST"),
        "away_shots_on_target":sval(row,"AST"),
        "home_fouls":sval(row,"HF"),
        "away_fouls":sval(row,"AF"),
        "home_corners":sval(row,"HC"),
        "away_corners":sval(row,"AC"),
        "home_yellows":sval(row,"HY"),
        "away_yellows":sval(row,"AY"),
        "home_reds":sval(row,"HR"),
        "away_reds":sval(row,"AR"),
        "b365_home":sval(row,"B365H"),
        "b365_draw":sval(row,"B365D"),
        "b365_away":sval(row,"B365A"),
        "avg_home":first(row,"AvgH","BbAvH"),
        "avg_draw":first(row,"AvgD","BbAvD"),
        "avg_away":first(row,"AvgA","BbAvA"),
        "b365_close_home":sval(row,"B365CH"),
        "b365_close_draw":sval(row,"B365CD"),
        "b365_close_away":sval(row,"B365CA"),
        "avg_close_home":sval(row,"AvgCH"),
        "avg_close_draw":sval(row,"AvgCD"),
        "avg_close_away":sval(row,"AvgCA"),
        "b365_over_25":first(row,"B365>2.5","B365O2.5"),
        "b365_under_25":first(row,"B365<2.5","B365U2.5"),
        "avg_over_25":first(row,"Avg>2.5","BbAv>2.5","AvgO2.5"),
        "avg_under_25":first(row,"Avg<2.5","BbAv<2.5","AvgU2.5"),
        "b365_close_over_25":sval(row,"B365C>2.5"),
        "b365_close_under_25":sval(row,"B365C<2.5"),
        "avg_close_over_25":sval(row,"AvgC>2.5"),
        "avg_close_under_25":sval(row,"AvgC<2.5"),
        "asian_handicap_line":first(row,"AHh","BbAHh"),
        "b365_ah_home":first(row,"B365AHH","B365AH"),
        "b365_ah_away":first(row,"B365AHA","B365AHA"),
        "avg_ah_home":first(row,"AvgAHH","BbAvAHH"),
        "avg_ah_away":first(row,"AvgAHA","BbAvAHA"),
        "asian_handicap_close_line":sval(row,"AHCh"),
        "b365_close_ah_home":sval(row,"B365CAHH"),
        "b365_close_ah_away":sval(row,"B365CAHA"),
        "avg_close_ah_home":sval(row,"AvgCAHH"),
        "avg_close_ah_away":sval(row,"AvgCAHA"),
        "source_row_number":str(row_number),
        "projection_version":VERSION,
        "historical_backfill_only":"true",
        "creates_signal":"false",
        "probability_mutation":"false",
        "eligibility_mutation":"false",
        "stake_changes":"false",
        "forward_journal_mutation":"false",
    }


def read_source_text(text,spec):
    reader=csv.DictReader(io.StringIO(text))
    rows=[]; invalid=0
    for idx,row in enumerate(reader,start=2):
        normalized=normalize_row(spec,row,idx)
        if normalized is None:
            invalid+=1
            continue
        rows.append(normalized)
    return rows,invalid,list(reader.fieldnames or [])


def fetch_specs(config,download_dir,timeout=30):
    download_dir=Path(download_dir)
    download_dir.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for spec in source_specs(config):
        target=download_dir/spec["filename"]
        req=urllib.request.Request(spec["url"],headers={"User-Agent":"PBK-historical-archive/1.0"})
        with urllib.request.urlopen(req,timeout=timeout) as response:
            data=response.read()
            status=getattr(response,"status",200)
        if status!=200 or not data:
            raise RuntimeError(f"download failed {status}: {spec['url']}")
        target.write_bytes(data)
        manifest.append({
            **spec,
            "bytes":len(data),
            "sha256":hashlib.sha256(data).hexdigest(),
        })
    return manifest


def normalize_directory(config,download_dir):
    all_rows=[]; sources=[]; total_invalid=0
    seen=set()
    for spec in source_specs(config):
        path=Path(download_dir)/spec["filename"]
        if not path.exists():
            sources.append({**spec,"present":False,"rows":0,"invalid_rows":0,"columns":[]})
            continue
        data=path.read_bytes()
        text=decode_csv_bytes(data)
        rows,invalid,columns=read_source_text(text,spec)
        duplicate=0
        for row in rows:
            mid=row["historical_match_id"]
            if mid in seen:
                duplicate+=1
                continue
            seen.add(mid); all_rows.append(row)
        total_invalid+=invalid
        sources.append({
            **spec,"present":True,"rows":len(rows)-duplicate,"invalid_rows":invalid,
            "duplicate_rows":duplicate,"columns":columns,"bytes":len(data),
            "sha256":hashlib.sha256(data).hexdigest(),
        })
    all_rows.sort(key=lambda r:(r["date_iso"],r["league_code"],r["home_team"],r["away_team"]))
    return all_rows,sources,total_invalid


def write_csv(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as stream:
        w=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def run(config_path,download_dir,out_csv,meta_out,fetch=False):
    config=load_config(config_path)
    download_manifest=fetch_specs(config,download_dir) if fetch else []
    rows,sources,invalid=normalize_directory(config,download_dir)
    write_csv(out_csv,rows)
    expected=len(config["seasons"])*len(config["leagues"])
    present=sum(1 for s in sources if s["present"])
    by_season={}
    by_league={}
    for row in rows:
        by_season[row["season_label"]]=by_season.get(row["season_label"],0)+1
        by_league[row["league_code"]]=by_league.get(row["league_code"],0)+1
    meta={
        "version":VERSION,
        "generated_at_utc":iso_now(),
        "scope":"Top-5 leagues; previous 9 completed seasons 2017/18-2025/26",
        "expected_source_files":expected,
        "present_source_files":present,
        "missing_source_files":expected-present,
        "normalized_matches":len(rows),
        "invalid_source_rows":invalid,
        "rows_by_season":dict(sorted(by_season.items())),
        "rows_by_league":dict(sorted(by_league.items())),
        "sources":sources,
        "download_manifest":download_manifest,
        "historical_backfill_only":True,
        "forward_validation_input":False,
        "current_operational_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
    }
    Path(meta_out).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    return meta


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config/stage80_football_data_top5_9seasons.json")
    p.add_argument("--download-dir",required=True)
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    p.add_argument("--fetch",action="store_true")
    a=p.parse_args()
    print(json.dumps(run(a.config,a.download_dir,a.out_csv,a.meta_out,a.fetch),ensure_ascii=False))


if __name__=="__main__":
    main()
