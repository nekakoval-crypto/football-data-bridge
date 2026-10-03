# PBK System Health

Обновлено UTC: 2026-10-03T02:06:16Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 19.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.16h | limit 1.5h
- Stage57 international: **OK** | age 19.25h | limit 30.0h
- Stage58 daily brief: **STALE** | age 7.01h | limit 3.0h
- Stage59 user execution: **STALE** | age 30.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 40.12h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 8.23h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.71h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 2.07h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.94h | limit 3.0h
- Stage71 challengers: **OK** | age 2.54h | limit 8.0h
- Stage71C team totals: **OK** | age 1.31h | limit 8.0h
- Stage71E double chance: **OK** | age 1.31h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.31h | limit 8.0h
- Stage71G DNB: **OK** | age 1.31h | limit 8.0h
- Stage71H readiness: **OK** | age 1.39h | limit 3.0h
- Stage71I settlement: **OK** | age 1.19h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.30h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.87h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 7.01h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 30.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 40.12h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 8.23h > 2.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.94h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.