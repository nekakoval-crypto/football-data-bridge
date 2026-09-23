# PBK System Health

Обновлено UTC: 2026-09-23T18:08:01Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 180 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.56h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.40h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.22h | limit 1.5h
- Stage57 international: **OK** | age 11.36h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.07h | limit 3.0h
- Stage59 user execution: **OK** | age 2.24h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.25h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.66h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.73h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.99h | limit 3.0h
- Stage71 challengers: **OK** | age 2.55h | limit 8.0h
- Stage71C team totals: **OK** | age 5.39h | limit 8.0h
- Stage71E double chance: **OK** | age 5.39h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.39h | limit 8.0h
- Stage71G DNB: **OK** | age 5.39h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.50h | limit 3.0h
- Stage71I settlement: **OK** | age 1.31h | limit 3.0h
- Stage72 data layer: **OK** | age 0.21h | limit 1.0h
- Stage73 internal API: **OK** | age 0.18h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.73h > 2.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.50h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.