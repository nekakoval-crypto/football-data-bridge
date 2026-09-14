# PBK System Health

Обновлено UTC: 2026-09-14T09:07:46Z
Статус: 🟠 **WARN** | critical 0 | warnings 1

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
- Stage53 screener: **OK** | age 2.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.13h | limit 1.5h
- Stage57 international: **OK** | age 2.33h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **OK** | age 1.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.21h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.18h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.26h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.83h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **OK** | age 1.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.92h | limit 3.0h
- Stage71 challengers: **OK** | age 0.80h | limit 8.0h
- Stage71C team totals: **OK** | age 2.35h | limit 8.0h
- Stage71E double chance: **OK** | age 2.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.35h | limit 8.0h
- Stage71G DNB: **OK** | age 2.35h | limit 8.0h
- Stage71H readiness: **OK** | age 2.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.29h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.79h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `SCHEMA_VERSION` — Expected Stage72 schema v6, got 11

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.

## API-Football budget guard
- Stage71J real calls: **177/190 per run**
- Shared-cache hits: **419**
- Child warnings: **0**
- Budget status: **OK**
