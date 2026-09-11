#!/usr/bin/env python3
"""Presentation-only adapter: expose familiar RU betting notation in Daily Brief.

Internal strategy/market codes remain unchanged. This file only adds display
labels and rewrites human-readable Markdown labels, so operational logic keeps
using stable English machine values.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
BRIEF_JSON = OPS / "daily_brief.json"
BRIEF_MD = OPS / "daily_brief.md"

SELECTION = {
    "Home": "П1",
    "Draw": "Х",
    "Away": "П2",
    "Over 2.5": "ТБ(2.5)",
    "Under 2.5": "ТМ(2.5)",
    "BTTS Yes": "ОЗ — Да",
    "BTTS No": "ОЗ — Нет",
}


def disp(value: str) -> str:
    return SELECTION.get(str(value or "").strip(), str(value or "").strip())


def main():
    if BRIEF_JSON.exists():
        payload = json.loads(BRIEF_JSON.read_text(encoding="utf-8"))
        for m in payload.get("matches", []) or []:
            m["display_selection"] = disp(m.get("selection") or "")
        if isinstance(payload.get("market_steam_watch"), dict):
            payload["market_steam_watch"]["display_market"] = "П1/П2 — движение коэффициента фаворита"
        if isinstance(payload.get("ou_steam_watch"), dict):
            payload["ou_steam_watch"]["display_selection"] = "ТБ(2.5)"
        if isinstance(payload.get("btts_market_watch"), dict):
            payload["btts_market_watch"]["display_market"] = "ОЗ — Да / ОЗ — Нет"
        payload.setdefault("display_policy", {})["bet_notation"] = (
            "User-facing: П1/Х/П2, 1Х/Х2/12, Ф1/Ф2, ТБ/ТМ, ОЗ — Да/Нет; machine codes unchanged"
        )
        BRIEF_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if BRIEF_MD.exists():
        text = BRIEF_MD.read_text(encoding="utf-8")
        for eng, ru in (("Selection: Home", "Ставка: П1"),
                        ("Selection: Draw", "Ставка: Х"),
                        ("Selection: Away", "Ставка: П2")):
            text = text.replace(eng, ru)
        text = text.replace("Trigger Bet365: H ", "Trigger Bet365: П1 ")
        text = text.replace(" / D ", " / Х ")
        text = text.replace(" / A ", " / П2 ")
        text = text.replace("Premier League Favorite Steam M1", "АПЛ: движение фаворита П1/П2")
        text = text.replace("opening favorite", "фаворит на opener")
        text = text.replace("Bundesliga Over 2.5 Steam O1", "Бундеслига: ТБ(2.5) — движение рынка")
        text = text.replace("Over 2.5", "ТБ(2.5)")
        text = text.replace("Under 2.5", "ТМ(2.5)")
        text = text.replace("Over crossings", "crossings ТБ(2.5)")
        BRIEF_MD.write_text(text, encoding="utf-8")

    print(json.dumps({"bet_display_notation": "RU", "machine_codes_changed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
