# PBK System Health

Обновлено UTC: 2026-09-27T21:05:56Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.19h | limit 1.5h
- Stage57 international: **OK** | age 14.33h | limit 30.0h
- Stage58 daily brief: **STALE** | age 9.04h | limit 3.0h
- Stage59 user execution: **OK** | age 2.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 8.16h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 6.63h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 6.73h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.85h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.18h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 5.55h | limit 8.0h
- Stage71C team totals: **STALE** | age 8.36h | limit 8.0h
- Stage71E double chance: **STALE** | age 8.36h | limit 8.0h
- Stage71F European handicap: **STALE** | age 8.36h | limit 8.0h
- Stage71G DNB: **STALE** | age 8.36h | limit 8.0h
- Stage71H readiness: **OK** | age 2.50h | limit 3.0h
- Stage71I settlement: **OK** | age 0.31h | limit 3.0h
- Stage72 data layer: **OK** | age 0.15h | limit 1.0h
- Stage73 internal API: **OK** | age 0.10h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 9.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 8.16h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 6.63h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 6.73h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.85h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 8.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 8.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 8.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 8.36h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.