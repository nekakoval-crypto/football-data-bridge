# PBK System Health

Обновлено UTC: 2026-09-28T19:07:35Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 12.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.28h | limit 3.0h
- Stage55 context: **OK** | age 0.79h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.31h | limit 1.5h
- Stage57 international: **OK** | age 12.29h | limit 30.0h
- Stage58 daily brief: **STALE** | age 9.04h | limit 3.0h
- Stage59 user execution: **OK** | age 0.15h | limit 3.0h
- Stage60 forward performance: **STALE** | age 3.16h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.12h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.66h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.75h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **STALE** | age 19.60h | limit 8.0h
- Stage71C team totals: **OK** | age 6.32h | limit 8.0h
- Stage71E double chance: **OK** | age 6.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 6.32h | limit 8.0h
- Stage71G DNB: **OK** | age 6.32h | limit 8.0h
- Stage71H readiness: **OK** | age 0.47h | limit 3.0h
- Stage71I settlement: **OK** | age 0.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.11h | limit 1.0h
- Stage73 internal API: **OK** | age 0.05h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.02h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 9.04h > 3.00h
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 3.16h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.12h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.66h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.75h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 19.60h > 8.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.91h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.