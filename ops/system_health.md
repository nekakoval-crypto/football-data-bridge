# PBK System Health

Обновлено UTC: 2026-09-12T01:04:58Z
Статус: 🟠 **WARN** | critical 0 | warnings 1

## Ключевые проверки
- Активные canonical: 3
- Frozen Marathonbet execution: 3/3
- Context coverage: 3/3
- WATCH crossings накоплено: 3
- Team Totals: openers 1311 | snapshots 7816
- Double Chance: openers 143 | snapshots 634
- European Handicap: openers 740 | snapshots 2768
- Ф(0): openers 127 | snapshots 463
- Stage72 Data Layer: integrity **ok** | tables 78 | schema v7
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.29h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.29h | limit 3.0h
- Stage55 context: **OK** | age 0.71h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **OK** | age 14.73h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.04h | limit 3.0h
- Stage59 user execution: **OK** | age 0.17h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.16h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.60h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.10h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.89h | limit 3.0h
- Stage71 challengers: **OK** | age 1.63h | limit 8.0h
- Stage71C team totals: **OK** | age 0.36h | limit 8.0h
- Stage71E double chance: **OK** | age 0.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.36h | limit 8.0h
- Stage71G DNB: **OK** | age 0.36h | limit 8.0h
- Stage71H readiness: **OK** | age 0.45h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.68h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.88h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.02h | limit 3.0h

## Проблемы
- **WARN** `SCHEMA_VERSION` — Expected Stage72 schema v6, got 7

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.

## API-Football budget guard
- Stage71J real calls: **177/190 per run**
- Shared-cache hits: **625**
- Child warnings: **0**
- Budget status: **OK**
