# PBK System Health

Обновлено UTC: 2026-09-12T12:07:22Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Активные canonical: 3
- Frozen Marathonbet execution: 3/3
- Context coverage: 3/3
- WATCH crossings накоплено: 3
- Team Totals: openers 1312 | snapshots 8799
- Double Chance: openers 143 | snapshots 742
- European Handicap: openers 740 | snapshots 3329
- Ф(0): openers 127 | snapshots 559
- Stage72 Data Layer: integrity **ok** | tables 78 | schema v7
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 5.60h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.43h | limit 3.0h
- Stage55 context: **OK** | age 0.88h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.21h | limit 1.5h
- Stage57 international: **OK** | age 5.39h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.07h | limit 3.0h
- Stage59 user execution: **OK** | age 0.27h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.26h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.69h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.34h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.88h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.00h | limit 3.0h
- Stage71 challengers: **OK** | age 4.66h | limit 8.0h
- Stage71C team totals: **OK** | age 5.41h | limit 8.0h
- Stage71E double chance: **OK** | age 5.41h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.41h | limit 8.0h
- Stage71G DNB: **OK** | age 5.41h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.52h | limit 3.0h
- Stage71I settlement: **OK** | age 1.37h | limit 3.0h
- Stage72 data layer: **OK** | age 0.21h | limit 1.0h
- Stage73 internal API: **OK** | age 0.85h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.52h > 3.00h
- **WARN** `SCHEMA_VERSION` — Expected Stage72 schema v6, got 7

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.

## API-Football budget guard
- Stage71J real calls: **177/190 per run**
- Shared-cache hits: **613**
- Child warnings: **0**
- Budget status: **OK**
