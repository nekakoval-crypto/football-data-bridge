# PBK System Health

Обновлено UTC: 2026-09-13T02:06:08Z
Статус: 🟠 **WARN** | critical 0 | warnings 1

## Ключевые проверки
- Активные canonical: 3
- Frozen Marathonbet execution: 3/3
- Context coverage: 3/3
- WATCH crossings накоплено: 6
- Team Totals: openers 1594 | snapshots 11043
- Double Chance: openers 173 | snapshots 989
- European Handicap: openers 896 | snapshots 4625
- Ф(0): openers 156 | snapshots 778
- Stage72 Data Layer: integrity **ok** | tables 79 | schema v8
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 19.58h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.38h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.34h | limit 1.5h
- Stage57 international: **OK** | age 19.37h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **OK** | age 0.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.21h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.29h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.71h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.98h | limit 3.0h
- Stage71 challengers: **OK** | age 2.64h | limit 8.0h
- Stage71C team totals: **OK** | age 1.36h | limit 8.0h
- Stage71E double chance: **OK** | age 1.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.36h | limit 8.0h
- Stage71G DNB: **OK** | age 1.36h | limit 8.0h
- Stage71H readiness: **OK** | age 1.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.83h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `SCHEMA_VERSION` — Expected Stage72 schema v6, got 8

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.

## API-Football budget guard
- Stage71J real calls: **177/190 per run**
- Shared-cache hits: **545**
- Child warnings: **0**
- Budget status: **OK**
