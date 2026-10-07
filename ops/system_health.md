# PBK System Health

Обновлено UTC: 2026-10-07T02:08:39Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 19.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **STALE** | age 59.73h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.14h | limit 3.0h
- Stage60 forward performance: **STALE** | age 43.05h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.58h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.23h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.66h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.23h | limit 3.0h
- Stage66 attention board: **OK** | age 2.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.89h | limit 3.0h
- Stage71 challengers: **OK** | age 2.46h | limit 8.0h
- Stage71C team totals: **OK** | age 1.24h | limit 8.0h
- Stage71E double chance: **OK** | age 1.24h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.24h | limit 8.0h
- Stage71G DNB: **OK** | age 1.24h | limit 8.0h
- Stage71H readiness: **OK** | age 1.32h | limit 3.0h
- Stage71I settlement: **OK** | age 1.13h | limit 3.0h
- Stage72 data layer: **OK** | age 0.21h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.98h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 59.73h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.14h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 43.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.