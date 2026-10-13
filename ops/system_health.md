# PBK System Health

Обновлено UTC: 2026-10-13T19:43:37Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 5.48h | limit 30.0h
- Stage54 odds/closing: **OK** | age 1.95h | limit 3.0h
- Stage55 context: **OK** | age 1.63h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 1.86h | limit 1.5h
- Stage57 international: **STALE** | age 60.85h | limit 30.0h
- Stage58 daily brief: **STALE** | age 18.68h | limit 3.0h
- Stage59 user execution: **OK** | age 2.54h | limit 3.0h
- Stage60 forward performance: **STALE** | age 51.73h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 11.18h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.46h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.88h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 2.01h | limit 3.0h
- Stage66 attention board: **STALE** | age 25.43h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 6.20h | limit 3.0h
- Stage71 challengers: **OK** | age 4.48h | limit 8.0h
- Stage71C team totals: **OK** | age 5.23h | limit 8.0h
- Stage71E double chance: **OK** | age 5.23h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.23h | limit 8.0h
- Stage71G DNB: **OK** | age 5.23h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.31h | limit 3.0h
- Stage71I settlement: **STALE** | age 3.29h | limit 3.0h
- Stage72 data layer: **STALE** | age 1.86h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.54h | limit 1.0h
- Stage68 exposure map: **STALE** | age 6.17h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage56 weather/XI: age 1.86h > 1.50h
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 60.85h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 18.68h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 51.73h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 11.18h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.88h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 25.43h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 6.20h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.31h > 3.00h
- **WARN** `STALE_STAGE` — Stage71I settlement: age 3.29h > 3.00h
- **WARN** `STALE_STAGE` — Stage72 data layer: age 1.86h > 1.00h
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.54h > 1.00h
- **WARN** `MISSING_USER_EXECUTION` — 4/10 active rows lack frozen executable Marathonbet paper price
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 6.17h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.