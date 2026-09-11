#!/usr/bin/env python3
"""Append Stage63 BTTS prospective WATCH status to Stage58 Daily Brief.

Presentation only. This never changes R1/R2/R3 or canonical forward rows.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
BRIEF_JSON = OPS / "daily_brief.json"
BRIEF_MD = OPS / "daily_brief.md"
META = OPS / "stage63_last_run.json"
OPENERS = OPS / "stage63_btts_openers.csv"
CROSSINGS = OPS / "stage63_btts_crossings.csv"
CLOSES = OPS / "stage63_btts_closes.csv"


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None


def pp(x):
    v = fnum(x)
    return "N/A" if v is None else f"{v*100:+.2f} п.п."


def main():
    if not BRIEF_JSON.exists() or not BRIEF_MD.exists():
        print("Stage63 brief adapter: Stage58 brief missing; nothing to append")
        return

    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    openers = read_csv(OPENERS)
    crossings = read_csv(CROSSINGS)
    closes = read_csv(CLOSES)
    closed_ids = {r.get("api_fixture_id") for r in closes if r.get("api_fixture_id")}
    active = [r for r in crossings if r.get("api_fixture_id") not in closed_ids]
    yes_active = [r for r in active if r.get("direction") == "YES"]
    no_active = [r for r in active if r.get("direction") == "NO"]

    watch = {
        "status": "PROSPECTIVE_RESEARCH_ONLY",
        "scope": "Big-5 ОЗ market movement",
        "display_market": "ОЗ — Да / ОЗ — Нет",
        "historical_edge_claimed": False,
        "historical_edge_reason": "Canonical 10-year dataset has no historical BTTS first/close odds",
        "canonical_forward_changed": False,
        "tracked_openers": len(openers),
        "active_crossings_total": len(active),
        "active_yes_crossings": len(yes_active),
        "active_no_crossings": len(no_active),
        "total_crossings": len(crossings),
        "observed_closes": len(closes),
        "movement_watch_threshold_pp": meta.get("movement_threshold_no_vig_pp", 0.03),
        "user_bookmaker": meta.get("user_bookmaker") or "Marathonbet",
        "latest_run_utc": meta.get("run_at_utc") or "",
        "warnings": meta.get("warnings") or [],
        "crossings": [
            {
                "fixture_id": r.get("api_fixture_id") or "",
                "league": r.get("league") or "",
                "home_team": r.get("home_team") or "",
                "away_team": r.get("away_team") or "",
                "selection": r.get("display_selection") or "",
                "movement_yes_pp": r.get("movement_yes_pp") or "",
                "crossed_at_utc": r.get("crossed_at_utc") or "",
                "minutes_to_kickoff": r.get("minutes_to_kickoff") or "",
                "user_selected_odds": r.get("user_cross_selected_odds") or "",
                "note": "research watch only; not a bet signal",
            }
            for r in active[-15:]
        ],
    }

    payload = json.loads(BRIEF_JSON.read_text(encoding="utf-8"))
    payload["btts_market_watch"] = watch
    BRIEF_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = BRIEF_MD.read_text(encoding="utf-8").rstrip()
    block = [
        "",
        "---",
        "",
        "# ОЗ MARKET WATCH — research only",
        "",
        "> Это **не ставка и не новая стратегия**. Исторического edge по ОЗ мы не заявляем: в 10-летней базе нет first/close коэффициентов ОЗ.",
        "",
        "- Рынок: ОЗ — Да / ОЗ — Нет, Big-5.",
        f"- Заморожено Bet365 opener'ов: {len(openers)}",
        f"- Активные движения ≥3 п.п.: всего {len(active)} | ОЗ — Да {len(yes_active)} | ОЗ — Нет {len(no_active)}",
        f"- Зафиксировано observed close: {len(closes)}",
        f"- Исполнимый букмекер для наблюдения: {watch['user_bookmaker']}",
    ]
    if active:
        block += ["", "## Текущие ОЗ-watch"]
        for r in active[-15:]:
            block.append(
                f"- WATCH | {r.get('league')} | {r.get('home_team')} — {r.get('away_team')} | "
                f"{r.get('display_selection')} | движение P(ОЗ — Да) {pp(r.get('movement_yes_pp'))} | "
                f"{watch['user_bookmaker']} {r.get('user_cross_selected_odds') or 'NO_PRICE'} | "
                f"{r.get('minutes_to_kickoff') or 'N/A'} мин до матча"
            )
    else:
        block += ["", "- Сейчас активных движений ≥3 п.п. по ОЗ нет."]

    BRIEF_MD.write_text(md + "\n" + "\n".join(block) + "\n", encoding="utf-8")
    print(json.dumps({
        "stage63_watch_appended": True,
        "tracked_openers": len(openers),
        "active_crossings": len(active),
        "historical_edge_claimed": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
