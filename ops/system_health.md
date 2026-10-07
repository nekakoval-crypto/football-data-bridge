# PBK System Health

Обновлено UTC: 2026-10-07T00:11:01Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.41h | limit 3.0h
- Stage55 context: **OK** | age 0.91h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.17h | limit 1.5h
- Stage57 international: **STALE** | age 57.77h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.11h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 41.09h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.64h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.30h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 11.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.14h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 5.99h | limit 3.0h
- Stage71 challengers: **OK** | age 0.50h | limit 8.0h
- Stage71C team totals: **OK** | age 5.37h | limit 8.0h
- Stage71E double chance: **OK** | age 5.37h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.37h | limit 8.0h
- Stage71G DNB: **OK** | age 5.37h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.48h | limit 3.0h
- Stage71I settlement: **OK** | age 1.33h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.03h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.01h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 57.77h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.11h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 41.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 11.81h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 5.99h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.48h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.