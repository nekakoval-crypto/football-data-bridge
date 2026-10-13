# PBK System Health

Обновлено UTC: 2026-10-13T12:25:40Z
Статус: 🔴 **CRITICAL** | critical 9 | warnings 11

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 20.94h | limit 30.0h
- Stage54 odds/closing: **OK** | age 2.71h | limit 3.0h
- Stage55 context: **OK** | age 2.04h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 1.67h | limit 1.5h
- Stage57 international: **STALE** | age 53.55h | limit 30.0h
- Stage58 daily brief: **STALE** | age 11.38h | limit 3.0h
- Stage59 user execution: **STALE** | age 10.15h | limit 3.0h
- Stage60 forward performance: **STALE** | age 44.44h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.88h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 8.89h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.93h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 1.95h | limit 3.0h
- Stage66 attention board: **STALE** | age 18.13h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 7.07h | limit 3.0h
- Stage71 challengers: **STALE** | age 8.69h | limit 8.0h
- Stage71C team totals: **STALE** | age 11.49h | limit 8.0h
- Stage71E double chance: **STALE** | age 11.49h | limit 8.0h
- Stage71F European handicap: **STALE** | age 11.49h | limit 8.0h
- Stage71G DNB: **STALE** | age 11.49h | limit 8.0h
- Stage71H readiness: **STALE** | age 11.56h | limit 3.0h
- Stage71I settlement: **STALE** | age 5.33h | limit 3.0h
- Stage72 data layer: **STALE** | age 2.78h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.95h | limit 1.0h
- Stage68 exposure map: **STALE** | age 6.99h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.07h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage56 weather/XI: age 1.67h > 1.50h
- **WARN** `STALE_STAGE` — Stage57 international: age 53.55h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 11.38h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 10.16h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 44.44h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.88h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 8.89h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.93h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 18.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 7.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 8.69h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 11.49h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 11.49h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 11.49h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 11.49h > 8.00h
- **CRITICAL** `STALE_STAGE` — Stage71H readiness: age 11.56h > 3.00h
- **WARN** `STALE_STAGE` — Stage71I settlement: age 5.33h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 2.78h > 1.00h
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.95h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 6.99h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.