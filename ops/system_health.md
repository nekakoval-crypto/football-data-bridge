# PBK System Health

Обновлено UTC: 2026-09-30T23:06:08Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.79h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.09h | limit 1.5h
- Stage57 international: **OK** | age 16.28h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.02h | limit 3.0h
- Stage59 user execution: **STALE** | age 30.14h | limit 3.0h
- Stage60 forward performance: **STALE** | age 25.18h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 6.13h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 5.66h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 10.67h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.11h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 23.57h | limit 8.0h
- Stage71C team totals: **STALE** | age 10.26h | limit 8.0h
- Stage71E double chance: **STALE** | age 10.25h | limit 8.0h
- Stage71F European handicap: **STALE** | age 10.25h | limit 8.0h
- Stage71G DNB: **STALE** | age 10.25h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.02h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.02h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 30.14h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 25.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 6.13h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 5.66h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 10.67h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 23.57h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 10.25h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 10.25h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 10.25h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 10.25h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.44h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.