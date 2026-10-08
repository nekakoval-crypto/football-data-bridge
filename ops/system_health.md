# PBK System Health

Обновлено UTC: 2026-10-08T22:09:18Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **STALE** | age 103.74h | limit 30.0h
- Stage58 daily brief: **STALE** | age 11.05h | limit 3.0h
- Stage59 user execution: **OK** | age 1.16h | limit 3.0h
- Stage60 forward performance: **STALE** | age 87.06h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.54h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.23h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.21h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 14.40h | limit 8.0h
- Stage71C team totals: **OK** | age 3.33h | limit 8.0h
- Stage71E double chance: **OK** | age 3.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.33h | limit 8.0h
- Stage71G DNB: **OK** | age 3.33h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.41h | limit 3.0h
- Stage71I settlement: **OK** | age 1.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.50h | limit 1.0h
- Stage73 internal API: **OK** | age 0.40h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 103.74h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 11.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 87.06h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.79h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.95h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 14.40h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.41h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.91h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.