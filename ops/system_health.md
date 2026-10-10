# PBK System Health

Обновлено UTC: 2026-10-10T23:06:48Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 2.32h | limit 3.0h
- Stage55 context: **OK** | age 2.84h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 2.50h | limit 1.5h
- Stage57 international: **OK** | age 16.25h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 12.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 136.02h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.24h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 1.51h | limit 3.0h
- Stage66 attention board: **OK** | age 2.06h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.94h | limit 3.0h
- Stage71 challengers: **OK** | age 7.37h | limit 8.0h
- Stage71C team totals: **OK** | age 4.32h | limit 8.0h
- Stage71E double chance: **OK** | age 4.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.32h | limit 8.0h
- Stage71G DNB: **OK** | age 4.32h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.43h | limit 3.0h
- Stage71I settlement: **OK** | age 2.25h | limit 3.0h
- Stage72 data layer: **STALE** | age 2.21h | limit 1.0h
- Stage73 internal API: **STALE** | age 2.09h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage56 weather/XI: age 2.50h > 1.50h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 12.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 136.02h > 3.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.24h > 2.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.94h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.43h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 2.21h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 2.09h > 1.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.96h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.