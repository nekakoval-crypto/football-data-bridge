# PBK System Health

Обновлено UTC: 2026-10-01T23:05:52Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.45h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.10h | limit 1.5h
- Stage57 international: **STALE** | age 40.27h | limit 30.0h
- Stage58 daily brief: **STALE** | age 8.01h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 13.11h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.11h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 6.21h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 10.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.92h | limit 3.0h
- Stage71 challengers: **STALE** | age 23.55h | limit 8.0h
- Stage71C team totals: **STALE** | age 10.27h | limit 8.0h
- Stage71E double chance: **STALE** | age 10.27h | limit 8.0h
- Stage71F European handicap: **STALE** | age 10.27h | limit 8.0h
- Stage71G DNB: **STALE** | age 10.27h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.40h | limit 3.0h
- Stage71I settlement: **OK** | age 0.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.27h | limit 1.0h
- Stage73 internal API: **OK** | age 0.19h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 40.27h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 8.01h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 13.11h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.11h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 6.21h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 10.70h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 23.55h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 10.27h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 10.27h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 10.27h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 10.27h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.40h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.