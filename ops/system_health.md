# PBK System Health

Обновлено UTC: 2026-10-09T12:11:02Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 5.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.88h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.38h | limit 1.5h
- Stage57 international: **STALE** | age 117.77h | limit 30.0h
- Stage58 daily brief: **STALE** | age 10.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.10h | limit 3.0h
- Stage60 forward performance: **STALE** | age 101.09h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 6.16h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.68h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 19.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.28h | limit 3.0h
- Stage66 attention board: **OK** | age 1.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.99h | limit 3.0h
- Stage71 challengers: **OK** | age 4.41h | limit 8.0h
- Stage71C team totals: **OK** | age 5.30h | limit 8.0h
- Stage71E double chance: **OK** | age 5.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.30h | limit 8.0h
- Stage71G DNB: **OK** | age 5.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.40h | limit 3.0h
- Stage71I settlement: **OK** | age 1.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.25h | limit 1.0h
- Stage68 exposure map: **STALE** | age 19.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 117.77h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 10.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.10h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 101.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 6.16h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 19.82h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.40h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 19.94h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.