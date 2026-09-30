# PBK System Health

Обновлено UTC: 2026-09-30T22:06:45Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **OK** | age 15.29h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 29.15h | limit 3.0h
- Stage60 forward performance: **STALE** | age 24.19h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 9.68h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **OK** | age 2.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **STALE** | age 22.58h | limit 8.0h
- Stage71C team totals: **STALE** | age 9.27h | limit 8.0h
- Stage71E double chance: **STALE** | age 9.27h | limit 8.0h
- Stage71F European handicap: **STALE** | age 9.27h | limit 8.0h
- Stage71G DNB: **STALE** | age 9.27h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.45h | limit 3.0h
- Stage71I settlement: **OK** | age 1.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.04h | limit 1.0h
- Stage68 exposure map: **STALE** | age 6.87h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 29.15h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 24.19h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.14h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.67h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 9.68h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 22.58h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 9.27h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 9.26h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 9.26h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 9.26h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.45h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 6.87h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.