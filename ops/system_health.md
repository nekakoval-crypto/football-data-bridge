# PBK System Health

Обновлено UTC: 2026-10-06T17:08:52Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 10.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.25h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.22h | limit 1.5h
- Stage57 international: **STALE** | age 50.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 8.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 23.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 34.05h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.54h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.21h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.77h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.19h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.93h | limit 3.0h
- Stage71 challengers: **OK** | age 1.46h | limit 8.0h
- Stage71C team totals: **OK** | age 4.30h | limit 8.0h
- Stage71E double chance: **OK** | age 4.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.30h | limit 8.0h
- Stage71G DNB: **OK** | age 4.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.41h | limit 3.0h
- Stage71I settlement: **OK** | age 0.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.06h | limit 1.0h
- Stage73 internal API: **OK** | age 0.07h | limit 1.0h
- Stage68 exposure map: **STALE** | age 34.86h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.01h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 50.73h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 8.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 23.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 34.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.21h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.77h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.08h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.41h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 34.86h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.