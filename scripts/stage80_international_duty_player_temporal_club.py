#!/usr/bin/env python3
"""Stage80 — conservative club-at-international-fixture-date projection.

Uses direct international player evidence + safe Transfermarkt identities +
durable historical transfer events. A club is derived only inside a bounded,
continuous transfer interval:

previous transfer.to == next transfer.from

No current-club substitution, no fuzzy club matching, and no unbounded
before-first/after-last inference.
"""
from __future__ import annotations

import csv, json, os
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

OPS=Path(os.getenv("OPS_DIR","ops"))
EVIDENCE=OPS/"international_duty_player_evidence.csv"
EVIDENCE_META=OPS/"stage80_international_duty_player_evidence_capture_last_run.json"
IDENTITY=OPS/"international_duty_player_identity_join.csv"
IDENTITY_META=OPS/"stage80_international_duty_player_identity_join_last_run.json"
TRANSFERS=OPS/"historical_transfer_events.csv"
TRANSFER_META=OPS/"stage80_transfer_history_last_run.json"
OUTPUT=OPS/"international_duty_player_temporal_club.csv"
META=OPS/"stage80_international_duty_player_temporal_club_last_run.json"

VERSION="PBK_STAGE80_INTERNATIONAL_DUTY_TEMPORAL_CLUB_V1_BOUNDED_CHAIN_ONLY"
EVIDENCE_VERSION="PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_EVIDENCE_CAPTURE_V2_STRICT_ROLE_SEMANTICS"
IDENTITY_VERSION="PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_IDENTITY_JOIN_V1_EXACT_ID_ONLY"
TRANSFER_VERSION="PBK_STAGE80_TRANSFER_HISTORY_ARCHIVE_V4_INTERNATIONAL_NAME_PROFILE_DOB"

FIELDS=[
"fixture_id","kickoff_utc","window_id","national_team_id","national_team_name",
"player_id","player_name","transfermarkt_player_id",
"temporal_club_status","transfermarkt_club_id","transfermarkt_club_name",
"interval_start_transfer_date","interval_end_transfer_date",
"previous_transfer_event_id","next_transfer_event_id","chain_match_method",
"transfer_date_collision","pbk16_club_identity_status",
"current_club_substituted","fuzzy_club_matching_used",
"provider_calls","research_only","operational_betting_authority","creates_signal",
"probability_mutation","eligibility_mutation","stake_changes","forward_journal_mutation"
]

def sval(r,k): return str((r or {}).get(k) or "").strip()

def read_csv(p):
    p=Path(p)
    if not p.exists(): return []
    with p.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))

def read_json(p):
    p=Path(p)
    if not p.exists(): return None
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {"_invalid_json":True}

def write_csv(p,rows):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    with t.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    t.replace(p)

def write_json(p,x):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8"); t.replace(p)

def parse_dt(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except Exception: return None

def parse_date(v):
    try: return datetime.fromisoformat(str(v)[:10]).date()
    except Exception: return None

def same_club(a_to_id,a_to_name,b_from_id,b_from_name):
    if a_to_id and b_from_id:
        return a_to_id==b_from_id, "TRANSFERMARKT_CLUB_ID"
    if a_to_name and b_from_name:
        return a_to_name==b_from_name, "EXACT_CLUB_NAME"
    return False, ""

def build(evidence_rows, identity_rows, transfer_rows):
    idmap={sval(r,"player_id"):r for r in identity_rows if sval(r,"player_id")}
    groups=defaultdict(list)
    for r in transfer_rows:
        pid=sval(r,"pbk_player_id")
        if pid: groups[pid].append(r)
    for pid in groups:
        groups[pid].sort(key=lambda r:(sval(r,"transfer_date"),sval(r,"transfer_event_id")))

    out=[]; invalid=0
    for e in evidence_rows:
        fid=sval(e,"fixture_id"); pid=sval(e,"player_id"); ko=parse_dt(e.get("kickoff_utc"))
        if not fid or not pid or ko is None:
            invalid+=1; continue
        ident=idmap.get(pid,{})
        tm=sval(ident,"transfermarkt_player_id")
        status=""; club_id=""; club_name=""; prev=None; nxt=None; method=""; collision=False
        events=[r for r in groups.get(pid,[]) if not tm or sval(r,"transfermarkt_player_id")==tm]
        target=ko.date()

        if not tm or sval(ident,"transfermarkt_identity_status")!="SAFE_AUTO_HIGH":
            status="NO_SAFE_TRANSFER_IDENTITY"
        elif not events:
            status="NO_TRANSFER_EVENTS"
        else:
            dated=[(parse_date(r.get("transfer_date")),r) for r in events]
            dated=[x for x in dated if x[0] is not None]
            if any(d==target for d,_ in dated):
                status="TRANSFER_DATE_COLLISION"; collision=True
            else:
                before=[x for x in dated if x[0]<target]
                after=[x for x in dated if x[0]>target]
                if not before or not after:
                    status="UNBOUNDED_INTERVAL"
                else:
                    prev=max(before,key=lambda x:(x[0],sval(x[1],"transfer_event_id")))[1]
                    nxt=min(after,key=lambda x:(x[0],sval(x[1],"transfer_event_id")))[1]
                    ok,method=same_club(
                        sval(prev,"to_club_id"),sval(prev,"to_club_name"),
                        sval(nxt,"from_club_id"),sval(nxt,"from_club_name")
                    )
                    if ok:
                        status="BOUNDED_CHAIN_CONFIRMED"
                        club_id=sval(prev,"to_club_id"); club_name=sval(prev,"to_club_name")
                    else:
                        status="CHAIN_BREAK"

        out.append({
            "fixture_id":fid,"kickoff_utc":sval(e,"kickoff_utc"),"window_id":sval(e,"window_id"),
            "national_team_id":sval(e,"national_team_id"),"national_team_name":sval(e,"national_team_name"),
            "player_id":pid,"player_name":sval(e,"player_name"),"transfermarkt_player_id":tm,
            "temporal_club_status":status,"transfermarkt_club_id":club_id,"transfermarkt_club_name":club_name,
            "interval_start_transfer_date":sval(prev,"transfer_date"),"interval_end_transfer_date":sval(nxt,"transfer_date"),
            "previous_transfer_event_id":sval(prev,"transfer_event_id"),"next_transfer_event_id":sval(nxt,"transfer_event_id"),
            "chain_match_method":method,"transfer_date_collision":"true" if collision else "false",
            "pbk16_club_identity_status":"NOT_DERIVED","current_club_substituted":"false",
            "fuzzy_club_matching_used":"false","provider_calls":"0","research_only":"true",
            "operational_betting_authority":"false","creates_signal":"false","probability_mutation":"false",
            "eligibility_mutation":"false","stake_changes":"false","forward_journal_mutation":"false",
        })
    out.sort(key=lambda r:(r["kickoff_utc"],r["fixture_id"],r["player_id"]))
    return out,invalid

def run(evidence_path=EVIDENCE,evidence_meta_path=EVIDENCE_META,identity_path=IDENTITY,
        identity_meta_path=IDENTITY_META,transfer_path=TRANSFERS,transfer_meta_path=TRANSFER_META,
        output_path=OUTPUT,meta_path=META):
    ev=read_csv(evidence_path); em=read_json(evidence_meta_path)
    ids=read_csv(identity_path); im=read_json(identity_meta_path)
    tr=read_csv(transfer_path); tm=read_json(transfer_meta_path)
    if not em or em.get("version")!=EVIDENCE_VERSION or int(em.get("evidence_rows") or 0)!=len(ev):
        raise ValueError("evidence contract not ready")
    if not im or im.get("version")!=IDENTITY_VERSION or im.get("status")!="OK":
        raise ValueError("identity contract not ready")
    if not tm or tm.get("version")!=TRANSFER_VERSION or int(tm.get("archive_rows") or 0)!=len(tr):
        raise ValueError("transfer archive contract not ready")

    rows,invalid=build(ev,ids,tr)
    keys=[(sval(r,"fixture_id"),sval(r,"player_id")) for r in rows]
    dup=len(keys)-len(set(keys))
    counts=Counter(sval(r,"temporal_club_status") for r in rows)
    bounded=sum(sval(r,"temporal_club_status")=="BOUNDED_CHAIN_CONFIRMED" for r in rows)
    bounded_players=len({sval(r,"player_id") for r in rows if sval(r,"temporal_club_status")=="BOUNDED_CHAIN_CONFIRMED"})
    invalid_out=sum(not (
        sval(r,"fixture_id") and sval(r,"player_id") and sval(r,"temporal_club_status")
        and sval(r,"pbk16_club_identity_status")=="NOT_DERIVED"
        and sval(r,"current_club_substituted")=="false"
        and sval(r,"fuzzy_club_matching_used")=="false"
        and sval(r,"provider_calls")=="0"
        and sval(r,"research_only")=="true"
        and sval(r,"operational_betting_authority")=="false"
    ) for r in rows)
    meta={
        "version":VERSION,"generated_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "status":"OK" if rows and not invalid and not dup and not invalid_out else "ATTENTION",
        "evidence_rows":len(ev),"output_rows":len(rows),"invalid_evidence_rows":invalid,
        "duplicate_fixture_player_rows":dup,"invalid_output_rows":invalid_out,
        "status_counts":dict(sorted(counts.items())),
        "bounded_chain_confirmed_rows":bounded,"bounded_chain_confirmed_players":bounded_players,
        "bounded_chain_coverage_pct":round(bounded/len(rows)*100,4) if rows else 0.0,
        "pbk16_club_identity_derived":False,"current_club_substituted":False,
        "unbounded_transfer_history_used_as_fact":False,"fuzzy_club_matching_used":False,
        "provider_calls":0,"research_only":True,"operational_betting_authority":False,
        "creates_signal":False,"probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
        "next_stage":"Build conservative Transfermarkt-club to PBK16-team identity for bounded rows only."
    }
    write_csv(output_path,rows); write_json(meta_path,meta); return meta

def main(): print(json.dumps(run(),ensure_ascii=False))
if __name__=="__main__": main()
