#!/usr/bin/env python3
"""Stage 66: PBK operational attention board.

Presentation-only layer. Reads existing prospective/canonical/watch/context files
and produces one compact user-facing screen of what deserves attention now.
It never creates a signal, changes a rule, changes a stake, or calls an API.
"""
from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OPS = Path(os.getenv("OPS_DIR", "ops"))
LOCAL_TZ = ZoneInfo(os.getenv("STAGE66_LOCAL_TZ", "Europe/Berlin"))

USER_FORWARD = OPS / "user_forward_view.csv"
CONTEXT = OPS / "context_latest.csv"
STAGE56 = OPS / "stage56_latest.csv"
ST61_OPEN = OPS / "stage61_market_openers.csv"
ST61_CROSS = OPS / "stage61_market_crossings.csv"
ST61_CLOSE = OPS / "stage61_market_closes.csv"
ST62_OPEN = OPS / "stage62_ou_openers.csv"
ST62_CROSS = OPS / "stage62_ou_crossings.csv"
ST62_CLOSE = OPS / "stage62_ou_closes.csv"
ST63_OPEN = OPS / "stage63_btts_openers.csv"
ST63_CROSS = OPS / "stage63_btts_crossings.csv"
ST63_CLOSE = OPS / "stage63_btts_closes.csv"
WATCH_LEDGER = OPS / "stage65_watch_ledger.csv"

OUT_JSON = OPS / "attention_board.json"
OUT_MD = OPS / "attention_board.md"
META = OPS / "stage66_last_run.json"


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def iso(dt):
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def local_text(dt):
    if not dt:
        return "TBD"
    return dt.astimezone(LOCAL_TZ).strftime("%d.%m %H:%M")


def fnum(v):
    try:
        x = float(str(v).strip())
        return x if math.isfinite(x) else None
    except Exception:
        return None


def selection_ru(sel):
    return {
        "Home": "П1",
        "Away": "П2",
        "Draw": "Х",
        "H": "П1",
        "A": "П2",
        "D": "Х",
        "YES": "ОЗ — Да",
        "NO": "ОЗ — Нет",
    }.get(str(sel or ""), str(sel or ""))


def latest_by(rows, key="forward_id", time_key="captured_at_utc"):
    out = {}
    for r in rows:
        k = r.get(key) or ""
        if not k:
            continue
        cur = out.get(k)
        if cur is None or (r.get(time_key) or "") > (cur.get(time_key) or ""):
            out[k] = r
    return out


def canonical_priority(row, ctx, s56, now):
    ko = parse_iso(row.get("kickoff_utc"))
    hrs = (ko - now).total_seconds() / 3600.0 if ko else None
    status = row.get("status") or ""
    lineup = (ctx.get("lineups_available") == "YES") or (s56.get("rotation_verified") == "YES")
    if status == "REVIEW":
        return "RED", "manual review"
    if lineup:
        return "RED", "официальный XI / ротация уже доступны"
    if hrs is not None and hrs <= 3:
        return "RED", "≤3ч до kickoff"
    if hrs is not None and hrs <= 24:
        return "ORANGE", "≤24ч до kickoff"
    return "BLUE", "активный canonical сигнал"


def canonical_note(ctx, s56):
    notes = []
    if ctx.get("away_prev_is_uefa_or_cup") == "YES":
        notes.append("гости после еврокубка/кубка")
    if ctx.get("away_next_is_uefa_or_cup") == "YES":
        notes.append("у гостей следующий матч еврокубок/кубок")
    if ctx.get("home_prev_is_uefa_or_cup") == "YES":
        notes.append("хозяева после еврокубка/кубка")
    if ctx.get("home_next_is_uefa_or_cup") == "YES":
        notes.append("у хозяев следующий матч еврокубок/кубок")
    if s56.get("rotation_verified") == "YES":
        notes.append("ротация подтверждена")
    elif ctx.get("lineups_available") == "YES":
        notes.append("официальные составы доступны")
    return "; ".join(notes) if notes else "контекст без срочных флагов"


def build_canonical(now):
    rows = read_csv(USER_FORWARD)
    ctx_by = latest_by(read_csv(CONTEXT))
    s56_by = latest_by(read_csv(STAGE56), time_key="weather_captured_at_utc")
    out = []
    for r in rows:
        if r.get("status") not in {"PAPER", "OPEN", "REVIEW"}:
            continue
        fid = r.get("forward_id") or ""
        ctx, s56 = ctx_by.get(fid, {}), s56_by.get(fid, {})
        level, reason = canonical_priority(r, ctx, s56, now)
        ko = parse_iso(r.get("kickoff_utc"))
        out.append({
            "type": "CANONICAL",
            "priority": level,
            "reason": reason,
            "forward_id": fid,
            "rule": r.get("rule") or "",
            "league": ctx.get("league") or "",
            "fixture_id": r.get("api_fixture_id") or "",
            "kickoff_utc": iso(ko),
            "kickoff_local": local_text(ko),
            "hours_to_kickoff": round((ko-now).total_seconds()/3600.0, 2) if ko else None,
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection": selection_ru(r.get("selection")),
            "paper_user_odds": r.get("paper_user_execution_odds") or "",
            "paper_user_book": r.get("paper_user_execution_bookmaker") or "",
            "status": r.get("status") or "",
            "context": canonical_note(ctx, s56),
            "snapshot_type": ctx.get("snapshot_type") or "",
        })
    order = {"RED": 0, "ORANGE": 1, "BLUE": 2}
    out.sort(key=lambda x: (order.get(x["priority"], 9), x.get("kickoff_utc") or ""))
    return out


def active_watch_rows(now):
    rows = []
    # Stage61: opening favorite steam, first crossing only.
    close61 = {r.get("api_fixture_id") for r in read_csv(ST61_CLOSE)}
    for r in read_csv(ST61_CROSS):
        fid = r.get("api_fixture_id") or ""
        ko = parse_iso(r.get("kickoff_utc"))
        if not ko or now >= ko or fid in close61:
            continue
        side = r.get("opening_favorite") or ""
        hrs = (ko-now).total_seconds()/3600.0
        rows.append({
            "type": "WATCH",
            "stage": "Stage61",
            "priority": "RED" if hrs <= 3 else "ORANGE",
            "league": "АПЛ",
            "fixture_id": fid,
            "kickoff_utc": iso(ko),
            "kickoff_local": local_text(ko),
            "hours_to_kickoff": round(hrs, 2),
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection": selection_ru(side),
            "movement_pp": r.get("movement_pp") or "",
            "user_book": r.get("user_bookmaker") or "Marathonbet",
            "user_odds": r.get("user_cross_odds") or "",
            "reason": "первый +3 п.п. steam фаворита",
        })
    # Stage62: Bundesliga Over 2.5 steam.
    close62 = {r.get("api_fixture_id") for r in read_csv(ST62_CLOSE)}
    for r in read_csv(ST62_CROSS):
        fid = r.get("api_fixture_id") or ""
        ko = parse_iso(r.get("kickoff_utc"))
        if not ko or now >= ko or fid in close62:
            continue
        hrs = (ko-now).total_seconds()/3600.0
        rows.append({
            "type": "WATCH",
            "stage": "Stage62",
            "priority": "RED" if hrs <= 3 else "ORANGE",
            "league": "Бундеслига",
            "fixture_id": fid,
            "kickoff_utc": iso(ko),
            "kickoff_local": local_text(ko),
            "hours_to_kickoff": round(hrs, 2),
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection": "ТБ(2.5)",
            "movement_pp": r.get("movement_pp") or "",
            "user_book": r.get("user_bookmaker") or "Marathonbet",
            "user_odds": r.get("user_cross_over25") or "",
            "reason": "первый +3 п.п. steam ТБ(2.5)",
        })
    # Stage63: Big-5 BTTS +/-3pp.
    close63 = {r.get("api_fixture_id") for r in read_csv(ST63_CLOSE)}
    for r in read_csv(ST63_CROSS):
        fid = r.get("api_fixture_id") or ""
        ko = parse_iso(r.get("kickoff_utc"))
        if not ko or now >= ko or fid in close63:
            continue
        hrs = (ko-now).total_seconds()/3600.0
        rows.append({
            "type": "WATCH",
            "stage": "Stage63",
            "priority": "RED" if hrs <= 3 else "ORANGE",
            "league": r.get("league") or "Big-5",
            "fixture_id": fid,
            "kickoff_utc": iso(ko),
            "kickoff_local": local_text(ko),
            "hours_to_kickoff": round(hrs, 2),
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection": r.get("display_selection") or selection_ru(r.get("direction")),
            "movement_pp": r.get("movement_yes_pp") or "",
            "user_book": r.get("user_bookmaker") or "Marathonbet",
            "user_odds": r.get("user_cross_selected_odds") or "",
            "reason": "prospective движение ОЗ ≥3 п.п.",
        })
    rows.sort(key=lambda x: (0 if x["priority"] == "RED" else 1, x.get("kickoff_utc") or ""))
    return rows


def nearest_monitored(now, limit_each=3):
    out = []
    def take(rows, stage, league, selection_fn, odds_fn):
        cand = []
        for r in rows:
            ko = parse_iso(r.get("kickoff_utc"))
            if not ko or ko <= now:
                continue
            cand.append((ko, r))
        cand.sort(key=lambda z: z[0])
        for ko, r in cand[:limit_each]:
            out.append({
                "type": "MONITOR",
                "stage": stage,
                "priority": "GRAY",
                "league": league if league else r.get("league") or "Big-5",
                "fixture_id": r.get("api_fixture_id") or "",
                "kickoff_utc": iso(ko),
                "kickoff_local": local_text(ko),
                "hours_to_kickoff": round((ko-now).total_seconds()/3600.0, 2),
                "home_team": r.get("home_team") or "",
                "away_team": r.get("away_team") or "",
                "market": selection_fn(r),
                "opener": odds_fn(r),
                "status": "наблюдение; crossing пока не зафиксирован",
            })
    take(read_csv(ST61_OPEN), "Stage61", "АПЛ", lambda r: "П1/П2 steam", lambda r: f"Bet365 {r.get('open_b365_home','')}/{r.get('open_b365_draw','')}/{r.get('open_b365_away','')}")
    take(read_csv(ST62_OPEN), "Stage62", "Бундеслига", lambda r: "ТБ(2.5) steam", lambda r: f"Bet365 ТБ {r.get('open_b365_over25','')} / ТМ {r.get('open_b365_under25','')}")
    take(read_csv(ST63_OPEN), "Stage63", "", lambda r: "ОЗ — Да / ОЗ — Нет", lambda r: f"Bet365 Да {r.get('open_b365_yes','')} / Нет {r.get('open_b365_no','')}")
    out.sort(key=lambda x: (x.get("kickoff_utc") or "", x.get("stage") or ""))
    return out


def recent_results(limit=8):
    rows = []
    for r in read_csv(USER_FORWARD):
        if r.get("status") not in {"SETTLED", "VOID"}:
            continue
        rows.append({
            "source": "CANONICAL",
            "rule": r.get("rule") or "",
            "kickoff_utc": r.get("kickoff_utc") or "",
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection": selection_ru(r.get("selection")),
            "result": r.get("result") or "",
            "profit_u": r.get("user_profit_u") or "",
        })
    for r in read_csv(WATCH_LEDGER):
        if r.get("status") not in {"SETTLED", "VOID"}:
            continue
        rows.append({
            "source": "WATCH",
            "rule": r.get("watch_type") or r.get("stage") or "WATCH",
            "kickoff_utc": r.get("kickoff_utc") or "",
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection": r.get("display_selection") or r.get("selection") or "",
            "result": r.get("result") or r.get("score") or "",
            "profit_u": r.get("user_profit_u") or r.get("profit_u") or "",
        })
    rows.sort(key=lambda x: x.get("kickoff_utc") or "", reverse=True)
    return rows[:limit]


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    canonical = build_canonical(now)
    watch = active_watch_rows(now)
    monitored = nearest_monitored(now)
    results = recent_results()

    red = [x for x in canonical + watch if x.get("priority") == "RED"]
    orange = [x for x in canonical + watch if x.get("priority") == "ORANGE"]
    blue = [x for x in canonical if x.get("priority") == "BLUE"]

    payload = {
        "generated_at_utc": iso(now),
        "generated_at_local": now.astimezone(LOCAL_TZ).isoformat(timespec="seconds"),
        "timezone": str(LOCAL_TZ),
        "status": "OK",
        "summary": {
            "red_attention": len(red),
            "orange_attention": len(orange),
            "blue_canonical": len(blue),
            "active_canonical": len(canonical),
            "active_watch_crossings": len(watch),
            "nearest_monitored_rows": len(monitored),
            "recent_results": len(results),
        },
        "red": red,
        "orange": orange,
        "canonical": canonical,
        "watch": watch,
        "nearest_monitored": monitored,
        "recent_results": results,
        "policy": {
            "presentation_only": True,
            "creates_signals": False,
            "changes_rules": False,
            "changes_stakes": False,
            "api_calls": False,
            "priority_red": "manual review, official XI/verified rotation, or <=3h to kickoff",
            "priority_orange": "<=24h to kickoff or active research WATCH crossing",
            "priority_blue": "active canonical signal >24h from kickoff",
            "priority_gray": "tracked opener only; no crossing/signal",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# PBK — Что требует внимания сейчас",
        "",
        f"Обновлено: {now.astimezone(LOCAL_TZ).strftime('%d.%m.%Y %H:%M')} ({LOCAL_TZ})",
        f"Canonical: {len(canonical)} | active WATCH crossings: {len(watch)} | RED: {len(red)} | ORANGE: {len(orange)}",
        "",
        "> Stage66 — только экран внимания. Он не создаёт ставки и не меняет R1/R2/R3.",
        "",
        "## 🔴 Срочно",
    ]
    if not red:
        md.append("- Сейчас срочных матчей нет.")
    else:
        for x in red:
            md.append(f"- **{x['home_team']} — {x['away_team']}** | {x.get('rule') or x.get('stage')} | {x.get('selection','')} | {x['kickoff_local']} | {x['reason']}")

    md += ["", "## 🟠 Ближайшие 24 часа / активные WATCH"]
    if not orange:
        md.append("- Сейчас нет событий уровня ORANGE.")
    else:
        for x in orange:
            price = f" | {x.get('user_odds')} @ {x.get('user_book')}" if x.get('user_odds') else ""
            md.append(f"- **{x['home_team']} — {x['away_team']}** | {x.get('rule') or x.get('stage')} | {x.get('selection','')} | {x['kickoff_local']} | {x['reason']}{price}")

    md += ["", "## 🔵 Активные R1/R2/R3"]
    if not canonical:
        md.append("- Активных canonical сигналов нет.")
    for x in canonical:
        price = f"{x['paper_user_odds']} @ {x['paper_user_book']}" if x.get("paper_user_odds") else "цена не заморожена"
        md.append(f"- **{x['rule']} | {x['home_team']} — {x['away_team']}** | {x['selection']} | {x['kickoff_local']} | {price} | {x['context']}")

    md += ["", "## 🟡 Research WATCH crossings"]
    if not watch:
        md.append("- Активных crossing-событий пока нет.")
    else:
        for x in watch:
            price = f"{x['user_odds']} @ {x['user_book']}" if x.get("user_odds") else "Marathonbet цена не зафиксирована"
            md.append(f"- **{x['stage']} | {x['home_team']} — {x['away_team']}** | {x['selection']} | {x['kickoff_local']} | {price}")

    md += ["", "## ⚪ Ближайшие матчи под наблюдением (без сигнала)"]
    if not monitored:
        md.append("- Нет ближайших monitored opener'ов.")
    else:
        for x in monitored:
            md.append(f"- **{x['stage']} | {x['home_team']} — {x['away_team']}** | {x['league']} | {x['kickoff_local']} | {x['market']} | {x['opener']}")

    md += ["", "## ✅ Последние рассчитанные результаты"]
    if not results:
        md.append("- Пока нет завершённых prospective ставок/WATCH для расчёта.")
    else:
        for x in results:
            pnl = f" | P/L {x['profit_u']}u" if x.get("profit_u") else ""
            md.append(f"- {x['source']} | **{x['home_team']} — {x['away_team']}** | {x['selection']} | {x['result']}{pnl}")

    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    meta = {
        "run_at_utc": iso(now),
        "status": "OK",
        "red_attention": len(red),
        "orange_attention": len(orange),
        "active_canonical": len(canonical),
        "active_watch_crossings": len(watch),
        "nearest_monitored_rows": len(monitored),
        "recent_results": len(results),
        "api_calls": 0,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
