# PBK System Health

Обновлено UTC: 2026-10-13T23:34:32Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.33h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.49h | limit 3.0h
- Stage55 context: **OK** | age 0.92h | limit 3.0h
- Stage56 weather/XI: **OK** | age 1.07h | limit 1.5h
- Stage57 international: **STALE** | age 64.70h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.91h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.38h | limit 3.0h
- Stage60 forward performance: **STALE** | age 55.58h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.97h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 5.31h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.41h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 1.60h | limit 3.0h
- Stage66 attention board: **STALE** | age 29.28h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.49h | limit 3.0h
- Stage71 challengers: **OK** | age 2.73h | limit 8.0h
- Stage71C team totals: **OK** | age 0.55h | limit 8.0h
- Stage71E double chance: **OK** | age 0.55h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.55h | limit 8.0h
- Stage71G DNB: **OK** | age 0.55h | limit 8.0h
- Stage71H readiness: **OK** | age 0.62h | limit 3.0h
- Stage71I settlement: **OK** | age 2.02h | limit 3.0h
- Stage72 data layer: **OK** | age 0.38h | limit 1.0h
- Stage73 internal API: **OK** | age 0.19h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.01h | limit 3.0h
- Stage69 promotion gate: **STALE** | age 3.89h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 64.70h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.38h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 55.58h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 5.31h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 29.28h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.49h > 3.00h
- **WARN** `MISSING_USER_EXECUTION` — 4/10 active rows lack frozen executable Marathonbet paper price
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.01h > 3.00h
- **WARN** `STALE_STAGE` — Stage69 promotion gate: age 3.89h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.