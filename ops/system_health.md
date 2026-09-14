# PBK System Health

Обновлено UTC: 2026-09-14T12:23:17Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 87 | schema v13
- Stage73 Internal API: tests **16/16** | API v1
- Optional stable sources pending: standings_snapshots.csv

## Свежесть этапов
- Stage53 screener: **OK** | age 5.79h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.62h | limit 3.0h
- Stage55 context: **OK** | age 0.01h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.41h | limit 1.5h
- Stage57 international: **OK** | age 5.59h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.33h | limit 3.0h
- Stage59 user execution: **OK** | age 1.49h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.46h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.44h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.52h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.02h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.26h | limit 3.0h
- Stage66 attention board: **OK** | age 0.37h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.20h | limit 3.0h
- Stage71 challengers: **OK** | age 4.06h | limit 8.0h
- Stage71C team totals: **OK** | age 5.61h | limit 8.0h
- Stage71E double chance: **OK** | age 5.61h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.61h | limit 8.0h
- Stage71G DNB: **OK** | age 5.61h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.70h | limit 3.0h
- Stage71I settlement: **OK** | age 1.56h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.06h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.18h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.30h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.70h > 3.00h
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.07h > 1.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.