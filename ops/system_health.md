# PBK System Health

Обновлено UTC: 2026-10-05T23:07:15Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.40h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **STALE** | age 32.71h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.14h | limit 3.0h
- Stage60 forward performance: **STALE** | age 16.02h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.56h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 6.63h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 16.66h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.03h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 11.92h | limit 3.0h
- Stage71 challengers: **STALE** | age 26.31h | limit 8.0h
- Stage71C team totals: **OK** | age 4.29h | limit 8.0h
- Stage71E double chance: **OK** | age 4.28h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.28h | limit 8.0h
- Stage71G DNB: **OK** | age 4.28h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.38h | limit 3.0h
- Stage71I settlement: **OK** | age 0.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.11h | limit 1.0h
- Stage73 internal API: **OK** | age 0.30h | limit 1.0h
- Stage68 exposure map: **STALE** | age 16.83h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 32.71h > 30.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.14h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 16.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 6.63h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 16.66h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 11.92h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 26.31h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.38h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 16.83h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.