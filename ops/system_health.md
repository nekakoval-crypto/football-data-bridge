# PBK System Health

Обновлено UTC: 2026-10-07T16:12:17Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.58h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.71h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.27h | limit 1.5h
- Stage57 international: **STALE** | age 73.79h | limit 30.0h
- Stage58 daily brief: **STALE** | age 7.09h | limit 3.0h
- Stage59 user execution: **STALE** | age 13.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 57.11h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.49h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.55h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 15.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **STALE** | age 6.11h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 6.00h | limit 3.0h
- Stage71 challengers: **STALE** | age 8.49h | limit 8.0h
- Stage71C team totals: **OK** | age 3.33h | limit 8.0h
- Stage71E double chance: **OK** | age 3.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.33h | limit 8.0h
- Stage71G DNB: **OK** | age 3.33h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.42h | limit 3.0h
- Stage71I settlement: **OK** | age 1.29h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.16h | limit 1.0h
- Stage68 exposure map: **STALE** | age 18.03h | limit 3.0h
- Stage69 promotion gate: **OK** | age 2.07h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 73.79h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 7.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 13.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 57.11h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.49h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 15.72h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 6.11h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 6.00h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 8.49h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.42h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 18.03h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.