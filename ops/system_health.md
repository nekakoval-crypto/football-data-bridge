# PBK System Health

Обновлено UTC: 2026-10-01T22:06:35Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.13h | limit 1.5h
- Stage57 international: **STALE** | age 39.28h | limit 30.0h
- Stage58 daily brief: **STALE** | age 7.02h | limit 3.0h
- Stage59 user execution: **OK** | age 2.19h | limit 3.0h
- Stage60 forward performance: **STALE** | age 12.13h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 6.12h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 5.22h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 9.71h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.11h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.93h | limit 3.0h
- Stage71 challengers: **STALE** | age 22.56h | limit 8.0h
- Stage71C team totals: **STALE** | age 9.28h | limit 8.0h
- Stage71E double chance: **STALE** | age 9.28h | limit 8.0h
- Stage71F European handicap: **STALE** | age 9.28h | limit 8.0h
- Stage71G DNB: **STALE** | age 9.28h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.41h | limit 3.0h
- Stage71I settlement: **OK** | age 1.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.05h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 39.28h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 7.02h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 12.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 6.12h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 5.22h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 9.71h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 22.56h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 9.28h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 9.28h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 9.28h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 9.28h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.41h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.