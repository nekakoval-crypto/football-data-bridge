# PBK System Health

Обновлено UTC: 2026-09-13T09:27:58Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Активные canonical: 3
- Frozen Marathonbet execution: 3/3
- Context coverage: 3/3
- WATCH crossings накоплено: 6
- Team Totals: openers 1594 | snapshots 11653
- Double Chance: openers 173 | snapshots 1056
- European Handicap: openers 897 | snapshots 4979
- Ф(0): openers 156 | snapshots 838
- Stage72 Data Layer: integrity **ok** | tables 79 | schema v8
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 2.88h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.64h | limit 3.0h
- Stage55 context: **OK** | age 1.18h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 2.70h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.07h | limit 3.0h
- Stage59 user execution: **OK** | age 0.33h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.58h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.24h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.07h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.19h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.93h | limit 3.0h
- Stage66 attention board: **OK** | age 0.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.31h | limit 3.0h
- Stage71 challengers: **OK** | age 1.99h | limit 8.0h
- Stage71C team totals: **OK** | age 2.72h | limit 8.0h
- Stage71E double chance: **OK** | age 2.72h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.72h | limit 8.0h
- Stage71G DNB: **OK** | age 2.72h | limit 8.0h
- Stage71H readiness: **OK** | age 2.80h | limit 3.0h
- Stage71I settlement: **OK** | age 2.62h | limit 3.0h
- Stage72 data layer: **OK** | age 0.37h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.15h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.31h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.01h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.15h > 1.00h
- **WARN** `SCHEMA_VERSION` — Expected Stage72 schema v6, got 8

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.

## API-Football budget guard
- Stage71J real calls: **177/190 per run**
- Shared-cache hits: **513**
- Child warnings: **0**
- Budget status: **OK**
