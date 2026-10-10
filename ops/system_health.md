# PBK System Health

Обновлено UTC: 2026-10-10T12:08:29Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 5.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.12h | limit 1.5h
- Stage57 international: **OK** | age 5.28h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.06h | limit 3.0h
- Stage59 user execution: **OK** | age 1.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 125.05h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.61h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.24h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.86h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 2.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.99h | limit 3.0h
- Stage71 challengers: **OK** | age 4.43h | limit 8.0h
- Stage71C team totals: **OK** | age 5.32h | limit 8.0h
- Stage71E double chance: **OK** | age 5.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.32h | limit 8.0h
- Stage71G DNB: **OK** | age 5.32h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.41h | limit 3.0h
- Stage71I settlement: **OK** | age 1.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.03h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 125.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.41h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.92h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.