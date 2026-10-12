# PBK System Health

Обновлено UTC: 2026-10-12T16:24:24Z
Статус: 🔴 **CRITICAL** | critical 9 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 0.92h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 6.72h | limit 3.0h
- Stage55 context: **STALE** | age 5.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.84h | limit 1.5h
- Stage57 international: **STALE** | age 33.53h | limit 30.0h
- Stage58 daily brief: **STALE** | age 7.71h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.61h | limit 3.0h
- Stage60 forward performance: **STALE** | age 24.41h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 17.43h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 15.88h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.31h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.83h | limit 3.0h
- Stage66 attention board: **STALE** | age 8.25h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 9.46h | limit 3.0h
- Stage71 challengers: **STALE** | age 13.81h | limit 8.0h
- Stage71C team totals: **OK** | age 0.50h | limit 8.0h
- Stage71E double chance: **OK** | age 0.50h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.50h | limit 8.0h
- Stage71G DNB: **OK** | age 0.50h | limit 8.0h
- Stage71H readiness: **OK** | age 0.63h | limit 3.0h
- Stage71I settlement: **OK** | age 0.32h | limit 3.0h
- Stage72 data layer: **OK** | age 0.28h | limit 1.0h
- Stage73 internal API: **OK** | age 0.18h | limit 1.0h
- Stage68 exposure map: **STALE** | age 29.70h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.07h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage54 odds/closing: age 6.72h > 3.00h
- **WARN** `STALE_STAGE` — Stage55 context: age 5.82h > 3.00h
- **WARN** `STALE_STAGE` — Stage57 international: age 33.53h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 7.71h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.61h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 24.41h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 17.43h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 15.88h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 8.25h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 9.46h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 13.81h > 8.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 29.70h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.