# PBK System Health

Обновлено UTC: 2026-10-10T07:08:47Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 0.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.24h | limit 3.0h
- Stage55 context: **OK** | age 0.77h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.25h | limit 1.5h
- Stage57 international: **OK** | age 0.28h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 120.05h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.62h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.67h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.20h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.97h | limit 3.0h
- Stage71 challengers: **OK** | age 7.45h | limit 8.0h
- Stage71C team totals: **OK** | age 0.32h | limit 8.0h
- Stage71E double chance: **OK** | age 0.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.32h | limit 8.0h
- Stage71G DNB: **OK** | age 0.32h | limit 8.0h
- Stage71H readiness: **OK** | age 0.41h | limit 3.0h
- Stage71I settlement: **OK** | age 0.19h | limit 3.0h
- Stage72 data layer: **OK** | age 0.07h | limit 1.0h
- Stage73 internal API: **OK** | age 0.49h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 120.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.67h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.08h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.