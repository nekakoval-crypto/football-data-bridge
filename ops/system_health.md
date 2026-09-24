# PBK System Health

Обновлено UTC: 2026-09-24T06:08:07Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 180 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 23.57h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.39h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.22h | limit 1.5h
- Stage57 international: **OK** | age 23.36h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.07h | limit 3.0h
- Stage59 user execution: **OK** | age 2.24h | limit 3.0h
- Stage60 forward performance: **STALE** | age 3.24h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.66h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.31h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.86h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.18h | limit 3.0h
- Stage66 attention board: **OK** | age 0.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.00h | limit 3.0h
- Stage71 challengers: **OK** | age 6.64h | limit 8.0h
- Stage71C team totals: **OK** | age 5.39h | limit 8.0h
- Stage71E double chance: **OK** | age 5.39h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.39h | limit 8.0h
- Stage71G DNB: **OK** | age 5.39h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.48h | limit 3.0h
- Stage71I settlement: **OK** | age 1.32h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.14h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.99h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 3.24h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.48h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.