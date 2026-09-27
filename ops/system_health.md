# PBK System Health

Обновлено UTC: 2026-09-27T23:06:03Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.19h | limit 1.5h
- Stage57 international: **OK** | age 16.33h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.05h | limit 3.0h
- Stage59 user execution: **OK** | age 0.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.22h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 8.63h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 8.74h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.85h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.19h | limit 3.0h
- Stage66 attention board: **OK** | age 1.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **OK** | age 7.56h | limit 8.0h
- Stage71C team totals: **STALE** | age 10.36h | limit 8.0h
- Stage71E double chance: **STALE** | age 10.36h | limit 8.0h
- Stage71F European handicap: **STALE** | age 10.36h | limit 8.0h
- Stage71G DNB: **STALE** | age 10.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.50h | limit 3.0h
- Stage71I settlement: **OK** | age 0.31h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.09h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 8.63h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 8.74h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.85h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 10.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 10.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 10.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 10.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.50h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.