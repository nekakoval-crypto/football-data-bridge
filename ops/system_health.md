# PBK System Health

Обновлено UTC: 2026-09-29T23:06:05Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **OK** | age 16.27h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.14h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.18h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 8.09h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 7.62h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.18h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **STALE** | age 23.55h | limit 8.0h
- Stage71C team totals: **STALE** | age 10.11h | limit 8.0h
- Stage71E double chance: **STALE** | age 10.11h | limit 8.0h
- Stage71F European handicap: **STALE** | age 10.11h | limit 8.0h
- Stage71G DNB: **STALE** | age 10.11h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.13h | limit 1.0h
- Stage73 internal API: **OK** | age 0.26h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.14h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 8.09h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 7.62h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.79h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 23.55h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 10.11h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 10.11h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 10.11h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 10.11h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.44h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.93h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.