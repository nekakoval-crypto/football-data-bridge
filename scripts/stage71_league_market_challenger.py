#!/usr/bin/env python3
"""Stage 71 — League & Market Challenger System.

Evidence board for the locked 16-league PBK universe. It does not mutate
canonical R-rules and does not automatically promote/suspend anything.

Current comparable family seed: exact R1/R2 definitions from the fixed Big-5
audit. New leagues remain DATA_REQUIRED until comparable historical evidence is
added. Prospective challenger rows can later be appended to the separate
stage71_challenger_forward.csv research ledger without changing this policy.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import stage53_daily_screener as s53

OPS = Path(os.getenv("OPS_DIR", "ops"))
SCOPE = Path("config/pbk_competition_scope.json")
SEED = Path("research/stage71_seed_evidence.csv")
PROSPECTIVE = OPS / "stage71_challenger_forward.csv"
USER_FORWARD = OPS / "user_forward_view.csv"
CATALOG = OPS / "stage71_league_catalog.csv"
OUT_CSV = OPS / "stage71_challenger_board.csv"
OUT_JSON = OPS / "stage71_challenger_board.json"
OUT_MD = OPS / "stage71_challenger_board.md"
META = OPS / "stage71_last_run.json"
SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))

ALIASES = {
    ("England", "Premier League"): ["Premier League"],
    ("Spain", "La Liga"): ["La Liga"],
    ("Italy", "Serie A"): ["Serie A"],
    ("Germany", "Bundesliga"): ["Bundesliga"],
    ("France", "Ligue 1"): ["Ligue 1"],
    ("Austria", "Austrian Bundesliga"): ["Bundesliga", "Austrian Bundesliga"],
    ("Belgium", "Belgian Pro League"): ["Jupiler Pro League", "Pro League", "First Division A"],
    ("Denmark", "Danish Superliga"): ["Superliga", "Danish Superliga"],
    ("Lithuania", "A Lyga"): ["A Lyga"],
    ("Latvia", "Virsliga"): ["Virsliga"],
    ("Netherlands", "Eredivisie"): ["Eredivisie"],
    ("Norway", "Eliteserien"): ["Eliteserien"],
    ("Poland", "Ekstraklasa"): ["Ekstraklasa"],
    ("Portugal", "Primeira Liga"): ["Primeira Liga"],
    ("Turkey", "Super Lig"): ["Süper Lig", "Super Lig"],
    ("Scotland", "Scottish Premiership"): ["Premiership", "Scottish Premiership"],
}

FIELDS = [
    "family", "country", "league", "group", "api_league_id", "api_league_name",
    "historical_status", "train_bets", "train_roi_pct", "test_bets", "test_roi_pct",
    "positive_seasons", "total_seasons", "prospective_settled", "prospective_roi_pct",
    "prospective_first_half_roi_pct", "prospective_second_half_roi_pct",
    "marathonbet_coverage_pct", "status", "leader", "blocking_reason"
]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def fnum(v):
    try:
        x = float(str(v).strip())
        return x if math.isfinite(x) else None
    except Exception:
        return None


def inum(v):
    try: return int(float(str(v).strip()))
    except Exception: return 0


def roi(rows):
    vals = [fnum(r.get("user_profit_u")) for r in rows]
    vals = [x for x in vals if x is not None]
    return (100.0 * sum(vals) / len(vals)) if vals else None


def prospective_metrics(rows):
    priced = [r for r in rows if fnum(r.get("user_odds") or r.get("user_cross_odds") or r.get("paper_user_execution_odds")) is not None]
    settled = [r for r in priced if str(r.get("status") or r.get("settlement_status") or "").upper() == "SETTLED" and fnum(r.get("user_profit_u")) is not None]
    settled.sort(key=lambda r: (r.get("kickoff_utc") or "", r.get("watch_id") or r.get("forward_id") or ""))
    cut = len(settled) // 2
    first, second = settled[:cut], settled[cut:]
    return {
        "rows": len(rows),
        "priced": len(priced),
        "coverage": 100.0 * len(priced) / len(rows) if rows else None,
        "settled": len(settled),
        "roi": roi(settled),
        "first_roi": roi(first),
        "second_roi": roi(second),
        "last60_roi": roi(settled[-60:]) if len(settled) >= 60 else None,
    }


def historical_gate(seed):
    if not seed:
        return False, "comparable historical evidence missing"
    tb, te = inum(seed.get("train_bets")), inum(seed.get("test_bets"))
    tr, ter = fnum(seed.get("train_roi_pct")), fnum(seed.get("test_roi_pct"))
    ps, ts = inum(seed.get("positive_seasons")), inum(seed.get("total_seasons"))
    reasons = []
    if tb < 150: reasons.append(f"TRAIN n {tb}<150")
    if te < 100: reasons.append(f"TEST n {te}<100")
    if tr is None or tr <= 0: reasons.append(f"TRAIN ROI {tr} not >0")
    if ter is None or ter <= 0: reasons.append(f"TEST ROI {ter} not >0")
    if ts and (100.0 * ps / ts) < 60.0: reasons.append(f"positive seasons {ps}/{ts}<60%")
    return not reasons, "; ".join(reasons)


def promotion_gate(m):
    reasons = []
    if m["settled"] < 60: reasons.append(f"prospective settled {m['settled']}/60")
    if m["coverage"] is None or m["coverage"] < 90: reasons.append(f"Marathonbet coverage {m['coverage']}% <90%")
    if m["roi"] is None or m["roi"] <= 0: reasons.append(f"forward ROI {m['roi']} not >0")
    if m["first_roi"] is None or m["first_roi"] <= 0: reasons.append(f"first-half ROI {m['first_roi']} not >0")
    if m["second_roi"] is None or m["second_roi"] <= 0: reasons.append(f"second-half ROI {m['second_roi']} not >0")
    return not reasons, "; ".join(reasons)


def degradation_status(m):
    if m["settled"] >= 100 and (m["roi"] is not None and m["roi"] <= 0) and (m["last60_roi"] is not None and m["last60_roi"] <= 0):
        return "SUSPENSION_REVIEW"
    if m["settled"] >= 60 and all(x is not None and x <= 0 for x in (m["roi"], m["first_roi"], m["second_roi"])):
        return "DEGRADATION_REVIEW"
    return "ACTIVE"


def norm(s):
    return " ".join(str(s or "").lower().replace("ü", "u").split())


def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def load_scope():
    data = json.loads(SCOPE.read_text(encoding="utf-8"))
    return list(data.get("core_big5", [])) + list(data.get("extended_final_scope", []))


def load_catalog_cache():
    return {(r.get("country"), r.get("league")): r for r in read_csv(CATALOG)}


def resolve_catalog(scope):
    cache = load_catalog_cache()
    out, api_calls, warnings = [], 0, []
    for x in scope:
        country, league = x["country"], x["league"]
        old = cache.get((country, league), {})
        api_id = old.get("api_league_id") or ""
        api_name = old.get("api_league_name") or ""
        if not api_id:
            try:
                d = s53.api_get("/leagues", {"country": country, "season": SEASON})
                api_calls += 1
                candidates = []
                for z in (d or {}).get("response", []):
                    li, co = z.get("league", {}) or {}, z.get("country", {}) or {}
                    if str(li.get("type") or "").lower() != "league":
                        continue
                    if norm(co.get("name")) != norm(country):
                        continue
                    nm = li.get("name") or ""
                    aliases = ALIASES.get((country, league), [league])
                    score = max(sim(nm, a) for a in aliases)
                    candidates.append((score, li.get("id"), nm))
                if candidates:
                    score, ident, nm = max(candidates)
                    if score >= 0.55:
                        api_id, api_name = str(ident), nm
                    else:
                        warnings.append(f"{country}/{league}: best API match too weak ({nm}, {score:.2f})")
                else:
                    warnings.append(f"{country}/{league}: no API league candidate for season {SEASON}")
            except Exception as e:
                warnings.append(f"{country}/{league}: API resolve error: {e}")
        out.append({
            "country": country, "league": league, "group": x.get("group") or "",
            "api_league_id": api_id, "api_league_name": api_name,
            "season": SEASON, "resolved": "YES" if api_id else "NO",
        })
    write_csv(CATALOG, ["country","league","group","api_league_id","api_league_name","season","resolved"], out)
    return out, api_calls, warnings


def canonical_rows_by_family_league():
    by = defaultdict(list)
    for r in read_csv(USER_FORWARD):
        fam = r.get("rule") or ""
        if fam not in {"R1", "R2"}: continue
        league = r.get("league") or "Serie A"
        by[(fam, league)].append(r)
    return by


def research_rows_by_family_league():
    by = defaultdict(list)
    for r in read_csv(PROSPECTIVE):
        fam, league = r.get("family") or "", r.get("league") or ""
        if fam and league: by[(fam, league)].append(r)
    return by


def main():
    now = now_iso(); OPS.mkdir(parents=True, exist_ok=True)
    scope = load_scope()
    catalog, api_calls, warnings = resolve_catalog(scope)
    catalog_by = {(r["country"], r["league"]): r for r in catalog}
    seeds = {(r.get("family"), r.get("league")): r for r in read_csv(SEED)}
    canonical = canonical_rows_by_family_league()
    research = research_rows_by_family_league()

    rows = []
    leaders = {}
    for family in ("R1", "R2"):
        family_rows = []
        for league_def in scope:
            country, league, group = league_def["country"], league_def["league"], league_def.get("group") or ""
            seed = seeds.get((family, league))
            hist_ok, hist_reason = historical_gate(seed)
            is_active_seed = bool(seed and seed.get("current_decision") == "ACTIVE_CANONICAL")
            p_rows = canonical.get((family, league), []) if is_active_seed else research.get((family, league), [])
            pm = prospective_metrics(p_rows)

            if is_active_seed:
                status = degradation_status(pm)
                block = "forward deterioration not evaluable before 60 settled" if pm["settled"] < 60 else ""
            elif seed and not hist_ok:
                status = "MONITORING_REJECTED_CURRENT_RULE"
                block = hist_reason
            elif hist_ok:
                pro_ok, pro_reason = promotion_gate(pm)
                status = "REVIEW_ELIGIBLE" if pro_ok else "CHALLENGER"
                block = "" if pro_ok else pro_reason
            else:
                status = "DATA_REQUIRED"
                block = hist_reason

            cat = catalog_by.get((country, league), {})
            row = {
                "family": family, "country": country, "league": league, "group": group,
                "api_league_id": cat.get("api_league_id") or "", "api_league_name": cat.get("api_league_name") or "",
                "historical_status": seed.get("current_decision") if seed else "NO_COMPARABLE_HISTORY",
                "train_bets": seed.get("train_bets") if seed else "", "train_roi_pct": seed.get("train_roi_pct") if seed else "",
                "test_bets": seed.get("test_bets") if seed else "", "test_roi_pct": seed.get("test_roi_pct") if seed else "",
                "positive_seasons": seed.get("positive_seasons") if seed else "", "total_seasons": seed.get("total_seasons") if seed else "",
                "prospective_settled": pm["settled"],
                "prospective_roi_pct": "" if pm["roi"] is None else round(pm["roi"], 3),
                "prospective_first_half_roi_pct": "" if pm["first_roi"] is None else round(pm["first_roi"], 3),
                "prospective_second_half_roi_pct": "" if pm["second_roi"] is None else round(pm["second_roi"], 3),
                "marathonbet_coverage_pct": "" if pm["coverage"] is None else round(pm["coverage"], 3),
                "status": status, "leader": "NO", "blocking_reason": block,
            }
            family_rows.append(row)

        active = [r for r in family_rows if r["status"] in {"ACTIVE", "DEGRADATION_REVIEW", "SUSPENSION_REVIEW"}]
        eligible = [r for r in family_rows if r["status"] == "REVIEW_ELIGIBLE"]
        leader = None
        if active:
            # Incumbent remains descriptive leader until a reviewed governance decision changes ACTIVE scope.
            leader = sorted(active, key=lambda r: (r["league"] != "Serie A", r["league"]))[0]
        elif eligible:
            leader = sorted(eligible, key=lambda r: fnum(r.get("prospective_roi_pct")) or -999, reverse=True)[0]
        if leader:
            leader["leader"] = "YES"; leaders[family] = leader["league"]
        rows.extend(family_rows)

    write_csv(OUT_CSV, FIELDS, rows)
    payload = {
        "generated_at_utc": now, "status": "OK", "scope_leagues": len(scope),
        "families": ["R1", "R2"], "leaders": leaders,
        "api_catalog_resolved": sum(1 for r in catalog if r.get("api_league_id")),
        "api_catalog_total": len(catalog), "api_calls": api_calls, "warnings": warnings,
        "automatic_promotion": "FORBIDDEN", "automatic_suspension": "FORBIDDEN",
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# PBK Stage71 — League & Market Challenger Board", "",
        f"Обновлено UTC: {now}",
        f"Scope: {len(scope)} лиг | API catalog: {payload['api_catalog_resolved']}/{len(scope)} | API calls this run: {api_calls}",
        "", "> Лидер — описательный статус. Stage71 не меняет canonical R1/R2 автоматически.", ""
    ]
    for family in ("R1", "R2"):
        md += [f"## {family} | текущий лидер: **{leaders.get(family, 'нет')}**", "", "| Лига | Статус | TRAIN ROI | TEST ROI | Forward settled | Forward ROI |", "|---|---|---:|---:|---:|---:|"]
        for r in [x for x in rows if x["family"] == family]:
            star = " 🏆" if r["leader"] == "YES" else ""
            md.append(f"| {r['league']}{star} | {r['status']} | {r['train_roi_pct'] or '—'} | {r['test_roi_pct'] or '—'} | {r['prospective_settled']} | {r['prospective_roi_pct'] if r['prospective_roi_pct'] != '' else '—'} |")
        md.append("")
    md += ["## Правило обновления", "- Здоровый ACTIVE не вытесняется автоматически.", "- Новый чемпионат может стать REVIEW_ELIGIBLE только после historical + prospective gate.", "- Если ACTIVE деградирует, открывается отдельный review; никакой автопаузы ставок.", "- Отсутствие данных = DATA_REQUIRED, а не нулевая эффективность."]
    if warnings:
        md += ["", "## Warnings"] + [f"- {w}" for w in warnings]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    META.write_text(json.dumps({
        "run_at_utc": now, "status": "OK", "scope_leagues": len(scope),
        "catalog_resolved": payload["api_catalog_resolved"], "catalog_total": len(scope),
        "r1_leader": leaders.get("R1"), "r2_leader": leaders.get("R2"),
        "review_eligible": sum(1 for r in rows if r["status"] == "REVIEW_ELIGIBLE"),
        "data_required": sum(1 for r in rows if r["status"] == "DATA_REQUIRED"),
        "warnings": len(warnings), "api_calls": api_calls,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"leaders": leaders, "catalog": f"{payload['api_catalog_resolved']}/{len(scope)}", "warnings": len(warnings)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
