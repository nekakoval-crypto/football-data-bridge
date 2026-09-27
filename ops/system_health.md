# PBK System Health

Обновлено UTC: 2026-09-27T22:05:54Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 15.33h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **OK** | age 0.23h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.22h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.63h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 7.73h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 7.85h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.20h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 6.55h | limit 8.0h
- Stage71C team totals: **STALE** | age 9.36h | limit 8.0h
- Stage71E double chance: **STALE** | age 9.36h | limit 8.0h
- Stage71F European handicap: **STALE** | age 9.36h | limit 8.0h
- Stage71G DNB: **STALE** | age 9.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.50h | limit 3.0h
- Stage71I settlement: **OK** | age 1.30h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.12h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.63h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 7.73h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 7.85h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 9.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 9.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 9.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 9.36h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.50h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.