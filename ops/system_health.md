# PBK System Health

Обновлено UTC: 2026-10-11T10:30:32Z
Статус: 🔴 **CRITICAL** | critical 11 | warnings 10

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 3.88h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 4.17h | limit 3.0h
- Stage55 context: **STALE** | age 3.52h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 5.40h | limit 1.5h
- Stage57 international: **OK** | age 3.63h | limit 30.0h
- Stage58 daily brief: **STALE** | age 14.44h | limit 3.0h
- Stage59 user execution: **STALE** | age 23.57h | limit 3.0h
- Stage60 forward performance: **STALE** | age 147.41h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 12.54h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.82h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.17h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 4.39h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.92h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 6.67h | limit 3.0h
- Stage71 challengers: **STALE** | age 10.87h | limit 8.0h
- Stage71C team totals: **STALE** | age 9.62h | limit 8.0h
- Stage71E double chance: **STALE** | age 9.62h | limit 8.0h
- Stage71F European handicap: **STALE** | age 9.62h | limit 8.0h
- Stage71G DNB: **STALE** | age 9.62h | limit 8.0h
- Stage71H readiness: **STALE** | age 9.70h | limit 3.0h
- Stage71I settlement: **OK** | age 1.20h | limit 3.0h
- Stage72 data layer: **STALE** | age 4.41h | limit 1.0h
- Stage73 internal API: **STALE** | age 3.42h | limit 1.0h
- Stage68 exposure map: **STALE** | age 17.36h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.70h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage54 odds/closing: age 4.17h > 3.00h
- **WARN** `STALE_STAGE` — Stage55 context: age 3.52h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage56 weather/XI: age 5.40h > 1.50h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 14.44h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 23.57h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 147.41h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 12.54h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.82h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.17h > 3.00h
- **WARN** `STALE_STAGE` — Stage65 WATCH performance: age 4.39h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.92h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 6.67h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 10.87h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 9.62h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 9.62h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 9.62h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 9.62h > 8.00h
- **CRITICAL** `STALE_STAGE` — Stage71H readiness: age 9.70h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 4.41h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 3.42h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 17.36h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.