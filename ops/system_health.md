# PBK System Health

Обновлено UTC: 2026-10-08T13:13:55Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 6.57h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.28h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.27h | limit 1.5h
- Stage57 international: **STALE** | age 94.82h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.12h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.25h | limit 3.0h
- Stage60 forward performance: **STALE** | age 78.14h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.62h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.63h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 12.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.13h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.99h | limit 3.0h
- Stage71 challengers: **OK** | age 5.48h | limit 8.0h
- Stage71C team totals: **OK** | age 0.35h | limit 8.0h
- Stage71E double chance: **OK** | age 0.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.35h | limit 8.0h
- Stage71G DNB: **OK** | age 0.35h | limit 8.0h
- Stage71H readiness: **OK** | age 0.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.21h | limit 3.0h
- Stage72 data layer: **OK** | age 0.57h | limit 1.0h
- Stage73 internal API: **OK** | age 0.46h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.01h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.09h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 94.82h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.25h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 78.14h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.62h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 12.78h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.13h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.01h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.