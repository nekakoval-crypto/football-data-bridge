# PBK System Health

Обновлено UTC: 2026-09-29T22:06:45Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **OK** | age 15.29h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.15h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.19h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.11h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 6.63h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 7.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.17h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **STALE** | age 22.57h | limit 8.0h
- Stage71C team totals: **STALE** | age 9.12h | limit 8.0h
- Stage71E double chance: **STALE** | age 9.12h | limit 8.0h
- Stage71F European handicap: **STALE** | age 9.12h | limit 8.0h
- Stage71G DNB: **STALE** | age 9.12h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.45h | limit 3.0h
- Stage71I settlement: **OK** | age 1.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.45h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.15h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.11h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 6.63h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 7.80h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 22.57h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 9.12h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 9.12h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 9.12h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 9.12h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.45h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.