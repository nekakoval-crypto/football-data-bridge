# PBK System Health

Обновлено UTC: 2026-10-06T02:07:58Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 19.41h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.11h | limit 1.5h
- Stage57 international: **STALE** | age 35.72h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 8.15h | limit 3.0h
- Stage60 forward performance: **STALE** | age 19.04h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 19.67h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **OK** | age 1.03h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.88h | limit 3.0h
- Stage71 challengers: **OK** | age 2.52h | limit 8.0h
- Stage71C team totals: **OK** | age 1.27h | limit 8.0h
- Stage71E double chance: **OK** | age 1.27h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.27h | limit 8.0h
- Stage71G DNB: **OK** | age 1.27h | limit 8.0h
- Stage71H readiness: **OK** | age 1.33h | limit 3.0h
- Stage71I settlement: **STALE** | age 3.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.22h | limit 1.0h
- Stage68 exposure map: **STALE** | age 19.85h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 35.72h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 8.15h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 19.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 19.67h > 3.00h
- **WARN** `STALE_STAGE` — Stage71I settlement: age 3.28h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 19.85h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.