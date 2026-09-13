# PBK System Health

Обновлено UTC: 2026-09-13T17:05:18Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Активные canonical: 3
- Frozen Marathonbet execution: 3/3
- Context coverage: 3/3
- WATCH crossings накоплено: 11
- Team Totals: openers 1638 | snapshots 12162
- Double Chance: openers 176 | snapshots 1111
- European Handicap: openers 913 | snapshots 5272
- Ф(0): openers 158 | snapshots 888
- Stage72 Data Layer: integrity **ok** | tables 84 | schema v10
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 4.28h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 10.33h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.04h | limit 3.0h
- Stage59 user execution: **OK** | age 0.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.22h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.27h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.16h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **OK** | age 1.55h | limit 8.0h
- Stage71C team totals: **OK** | age 4.37h | limit 8.0h
- Stage71E double chance: **OK** | age 4.37h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.37h | limit 8.0h
- Stage71G DNB: **OK** | age 4.37h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.49h | limit 3.0h
- Stage71I settlement: **OK** | age 0.30h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.79h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.48h > 3.00h
- **WARN** `SCHEMA_VERSION` — Expected Stage72 schema v6, got 10

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.

## API-Football budget guard
- Stage71J real calls: **177/190 per run**
- Shared-cache hits: **497**
- Child warnings: **0**
- Budget status: **OK**
