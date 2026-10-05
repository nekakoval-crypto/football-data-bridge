# PBK System Health

Обновлено UTC: 2026-10-05T06:13:22Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 15.81h | limit 30.0h
- Stage58 daily brief: **STALE** | age 19.25h | limit 3.0h
- Stage59 user execution: **STALE** | age 12.08h | limit 3.0h
- Stage60 forward performance: **STALE** | age 35.48h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.20h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.29h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.77h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.29h | limit 3.0h
- Stage66 attention board: **OK** | age 0.14h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.07h | limit 3.0h
- Stage71 challengers: **STALE** | age 9.41h | limit 8.0h
- Stage71C team totals: **OK** | age 5.36h | limit 8.0h
- Stage71E double chance: **OK** | age 5.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.36h | limit 8.0h
- Stage71G DNB: **OK** | age 5.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.43h | limit 3.0h
- Stage71I settlement: **OK** | age 1.01h | limit 3.0h
- Stage72 data layer: **OK** | age 0.13h | limit 1.0h
- Stage73 internal API: **OK** | age 0.03h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.87h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 19.25h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 12.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 35.48h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.77h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 9.41h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.43h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.