# PBK System Health

Обновлено UTC: 2026-10-09T16:10:05Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **STALE** | age 121.75h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 9.09h | limit 3.0h
- Stage60 forward performance: **STALE** | age 105.07h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.51h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.69h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 23.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.11h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **OK** | age 0.41h | limit 8.0h
- Stage71C team totals: **OK** | age 3.31h | limit 8.0h
- Stage71E double chance: **OK** | age 3.31h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.31h | limit 8.0h
- Stage71G DNB: **OK** | age 3.31h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.41h | limit 3.0h
- Stage71I settlement: **OK** | age 1.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.23h | limit 1.0h
- Stage68 exposure map: **STALE** | age 23.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.02h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 121.75h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 9.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 105.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 23.80h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.10h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.41h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 23.93h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.