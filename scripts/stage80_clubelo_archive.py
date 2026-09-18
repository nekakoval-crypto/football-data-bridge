#!/usr/bin/env python3
"""Stage80 — append-only ClubElo daily strength archive.

ClubElo is external enrichment, never canonical PBK probability authority.
This collector calls the public daily CSV endpoint and archives point-in-time
ratings with explicit provenance. It does not call API-Football.

Identity: snapshot_date + club + country.
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
LEDGER = OPS / "clubelo_daily_snapshots.csv"
META = OPS / "stage80_clubelo_last_run.json"
VERSION = "PBK_STAGE80_CLUBELO_DAILY_ARCHIVE_V1"

FIELDS = [
    "snapshot_date","observed_at_utc","rank","club","country","level","elo",
    "effective_from","effective_to","source_url","source","archive_version",
    "historical_enrichment_only","current_operational_authority","creates_signal",
    "probability_mutation","eligibility_mutation","stake_changes","forward_journal_mutation",
]


def iso_now(value=None):
    value=value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_csv(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv_atomic(path, rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    tmp.replace(path)


def normalize_text(text, snapshot_date, observed_at, source_url):
    reader=csv.DictReader(io.StringIO(text))
    rows=[]; invalid=0
    for raw in reader:
        club=str(raw.get("Club") or "").strip()
        country=str(raw.get("Country") or "").strip()
        elo=str(raw.get("Elo") or "").strip()
        if not club or not country or not elo:
            invalid += 1
            continue
        rows.append({
            "snapshot_date":snapshot_date,
            "observed_at_utc":observed_at,
            "rank":str(raw.get("Rank") or "").strip(),
            "club":club,
            "country":country,
            "level":str(raw.get("Level") or "").strip(),
            "elo":elo,
            "effective_from":str(raw.get("From") or "").strip(),
            "effective_to":str(raw.get("To") or "").strip(),
            "source_url":source_url,
            "source":"clubelo.com",
            "archive_version":VERSION,
            "historical_enrichment_only":"true",
            "current_operational_authority":"false",
            "creates_signal":"false",
            "probability_mutation":"false",
            "eligibility_mutation":"false",
            "stake_changes":"false",
            "forward_journal_mutation":"false",
        })
    return rows,invalid,list(reader.fieldnames or [])


def key(row):
    return (
        str(row.get("snapshot_date") or "").strip(),
        str(row.get("club") or "").strip(),
        str(row.get("country") or "").strip(),
    )


def merge_rows(existing,incoming):
    merged={}
    invalid_existing=0
    duplicates_existing=0
    for row in existing:
        k=key(row)
        if not all(k):
            invalid_existing += 1
            continue
        if k in merged:
            duplicates_existing += 1
            continue
        merged[k]=dict(row)
    added=duplicates_incoming=invalid_incoming=0
    for row in incoming:
        k=key(row)
        if not all(k):
            invalid_incoming += 1
            continue
        if k in merged:
            duplicates_incoming += 1
            continue
        merged[k]=dict(row); added += 1
    return {
        "rows":[merged[k] for k in sorted(merged)],
        "added_rows":added,
        "duplicate_incoming_rows":duplicates_incoming,
        "duplicate_existing_rows":duplicates_existing,
        "invalid_incoming_rows":invalid_incoming,
        "invalid_existing_rows":invalid_existing,
    }


def fetch_snapshot(snapshot_date, attempts=4, timeout=45):
    urls=[
        f"https://api.clubelo.com/{snapshot_date}",
        f"http://api.clubelo.com/{snapshot_date}",
    ]
    last=None
    for attempt in range(1,max(1,int(attempts))+1):
        for url in urls:
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"PBK-archive/1.0 (+source attribution in repository)"})
                with urllib.request.urlopen(req,timeout=timeout) as response:
                    data=response.read()
                    status=getattr(response,"status",200)
                text=data.decode("utf-8-sig",errors="replace")
                if status==200 and text.lstrip().startswith("Rank,Club"):
                    return text,url
                last=RuntimeError(f"unexpected ClubElo response {status}: {url}")
            except (urllib.error.URLError,urllib.error.HTTPError,TimeoutError,OSError) as exc:
                last=exc
        if attempt < attempts:
            time.sleep(min(12,attempt*3))
    raise RuntimeError(f"ClubElo snapshot unavailable for {snapshot_date}: {last}")


def build(snapshot_date, observed_at, existing, text, source_url):
    incoming,invalid_source,columns=normalize_text(text,snapshot_date,observed_at,source_url)
    merged=merge_rows(existing,incoming)
    return {
        **merged,
        "source_rows":len(incoming),
        "invalid_source_rows":invalid_source,
        "source_columns":columns,
    }


def main():
    now=datetime.now(timezone.utc)
    snapshot_date=os.getenv("STAGE80_CLUBELO_DATE",now.date().isoformat()).strip()
    text,source_url=fetch_snapshot(snapshot_date)
    existing=read_csv(LEDGER)
    result=build(snapshot_date,iso_now(now),existing,text,source_url)
    write_csv_atomic(LEDGER,result["rows"])
    status="ATTENTION" if any([
        result["invalid_source_rows"],result["invalid_incoming_rows"],result["invalid_existing_rows"]
    ]) else "OK"
    meta={
        "version":VERSION,
        "run_at_utc":iso_now(now),
        "status":status,
        "snapshot_date":snapshot_date,
        "source_url":source_url,
        "source_rows":result["source_rows"],
        "added_rows":result["added_rows"],
        "total_rows":len(result["rows"]),
        "invalid_source_rows":result["invalid_source_rows"],
        "duplicate_incoming_rows":result["duplicate_incoming_rows"],
        "source_columns":result["source_columns"],
        "identity":"snapshot_date+club+country",
        "provider_calls":0,
        "external_source_calls":1,
        "historical_enrichment_only":True,
        "current_operational_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
        "attribution":"ClubElo.com / Lars Schiefler",
    }
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(meta,ensure_ascii=False))
    if status=="ATTENTION":
        raise SystemExit(2)


if __name__=="__main__":
    main()
