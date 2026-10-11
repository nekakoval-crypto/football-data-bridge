# PBK System Health

Обновлено UTC: 2026-10-11T03:19:28Z
Статус: 🔴 **CRITICAL** | critical 8 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 20.71h | limit 30.0h
- Stage54 odds/closing: **OK** | age 2.91h | limit 3.0h
- Stage55 context: **STALE** | age 3.13h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 3.41h | limit 1.5h
- Stage57 international: **OK** | age 20.46h | limit 30.0h
- Stage58 daily brief: **STALE** | age 7.26h | limit 3.0h
- Stage59 user execution: **STALE** | age 16.39h | limit 3.0h
- Stage60 forward performance: **STALE** | age 140.23h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.36h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.48h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.05h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 2.87h | limit 3.0h
- Stage66 attention board: **OK** | age 2.75h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.11h | limit 3.0h
- Stage71 challengers: **OK** | age 3.69h | limit 8.0h
- Stage71C team totals: **OK** | age 2.43h | limit 8.0h
- Stage71E double chance: **OK** | age 2.43h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.43h | limit 8.0h
- Stage71G DNB: **OK** | age 2.43h | limit 8.0h
- Stage71H readiness: **OK** | age 2.51h | limit 3.0h
- Stage71I settlement: **OK** | age 2.07h | limit 3.0h
- Stage72 data layer: **STALE** | age 3.35h | limit 1.0h
- Stage73 internal API: **STALE** | age 3.07h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.17h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.40h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage55 context: age 3.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage56 weather/XI: age 3.41h > 1.50h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 7.26h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 16.39h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 140.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.36h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.48h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.11h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 3.35h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 3.07h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.17h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.