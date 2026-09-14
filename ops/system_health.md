# PBK System Health

Обновлено UTC: 2026-09-14T10:06:24Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Активные canonical: 2
- Frozen Marathonbet execution: 2/2
- Context coverage: 2/2
- WATCH crossings накоплено: 11
- Team Totals: openers 1772 | snapshots 12638
- Double Chance: openers 191 | snapshots 1164
- European Handicap: openers 989 | snapshots 5552
- Ф(0): openers 171 | snapshots 935
- Stage72 Data Layer: integrity **ok** | tables 85 | schema v11
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 3.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.79h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.12h | limit 1.5h
- Stage57 international: **OK** | age 3.31h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **OK** | age 2.19h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.18h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.23h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **OK** | age 1.78h | limit 8.0h
- Stage71C team totals: **OK** | age 3.33h | limit 8.0h
- Stage71E double chance: **OK** | age 3.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.33h | limit 8.0h
- Stage71G DNB: **OK** | age 3.33h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.42h | limit 3.0h
- Stage71I settlement: **OK** | age 1.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.77h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.42h > 3.00h
- **WARN** `SCHEMA_VERSION` — Expected Stage72 schema v6, got 11

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.

## API-Football budget guard
- Stage71J real calls: **177/190 per run**
- Shared-cache hits: **419**
- Child warnings: **0**
- Budget status: **OK**
