# PBK System Health

Обновлено UTC: 2026-10-06T18:08:59Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.15h | limit 1.5h
- Stage57 international: **STALE** | age 51.73h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **OK** | age 0.19h | limit 3.0h
- Stage60 forward performance: **STALE** | age 35.05h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.54h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.21h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.77h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **STALE** | age 6.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.93h | limit 3.0h
- Stage71 challengers: **OK** | age 2.46h | limit 8.0h
- Stage71C team totals: **OK** | age 5.30h | limit 8.0h
- Stage71E double chance: **OK** | age 5.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.30h | limit 8.0h
- Stage71G DNB: **OK** | age 5.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.41h | limit 3.0h
- Stage71I settlement: **OK** | age 1.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.41h | limit 1.0h
- Stage68 exposure map: **STALE** | age 35.86h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 51.73h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 35.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.21h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.77h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 6.09h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.41h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 35.86h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.