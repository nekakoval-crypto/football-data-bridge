# PBK System Health

Обновлено UTC: 2026-09-30T16:09:54Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.34h | limit 1.5h
- Stage57 international: **OK** | age 9.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 23.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 18.25h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.24h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.73h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 16.63h | limit 8.0h
- Stage71C team totals: **OK** | age 3.32h | limit 8.0h
- Stage71E double chance: **OK** | age 3.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.32h | limit 8.0h
- Stage71G DNB: **OK** | age 3.32h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.40h | limit 3.0h
- Stage71I settlement: **OK** | age 1.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.43h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 23.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 18.25h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.73h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.95h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 16.63h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.40h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.