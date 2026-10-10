# PBK System Health

Обновлено UTC: 2026-10-10T22:06:45Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 1.32h | limit 3.0h
- Stage55 context: **OK** | age 1.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 1.50h | limit 1.5h
- Stage57 international: **OK** | age 15.25h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 11.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 135.02h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.24h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 9.76h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.51h | limit 3.0h
- Stage66 attention board: **OK** | age 1.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.94h | limit 3.0h
- Stage71 challengers: **OK** | age 6.37h | limit 8.0h
- Stage71C team totals: **OK** | age 3.32h | limit 8.0h
- Stage71E double chance: **OK** | age 3.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.32h | limit 8.0h
- Stage71G DNB: **OK** | age 3.32h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.43h | limit 3.0h
- Stage71I settlement: **OK** | age 1.25h | limit 3.0h
- Stage72 data layer: **STALE** | age 1.21h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.09h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.02h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 11.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 135.02h > 3.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.24h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 9.76h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.43h > 3.00h
- **WARN** `STALE_STAGE` — Stage72 data layer: age 1.21h > 1.00h
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.09h > 1.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.96h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.