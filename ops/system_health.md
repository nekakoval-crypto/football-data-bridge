# PBK System Health

Обновлено UTC: 2026-10-08T06:11:07Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 23.56h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.36h | limit 1.5h
- Stage57 international: **STALE** | age 87.77h | limit 30.0h
- Stage58 daily brief: **STALE** | age 21.07h | limit 3.0h
- Stage59 user execution: **OK** | age 0.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 71.09h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.65h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.25h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.73h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.25h | limit 3.0h
- Stage66 attention board: **OK** | age 0.11h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.01h | limit 3.0h
- Stage71 challengers: **OK** | age 6.52h | limit 8.0h
- Stage71C team totals: **OK** | age 5.30h | limit 8.0h
- Stage71E double chance: **OK** | age 5.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.30h | limit 8.0h
- Stage71G DNB: **OK** | age 5.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.37h | limit 3.0h
- Stage71I settlement: **OK** | age 1.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.30h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 87.77h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 21.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 71.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.65h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.73h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.01h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.37h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.94h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.