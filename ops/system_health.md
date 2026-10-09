# PBK System Health

Обновлено UTC: 2026-10-09T18:09:51Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.88h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.15h | limit 1.5h
- Stage57 international: **STALE** | age 123.75h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 11.08h | limit 3.0h
- Stage60 forward performance: **STALE** | age 107.07h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.69h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 25.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **STALE** | age 7.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.96h | limit 3.0h
- Stage71 challengers: **OK** | age 2.41h | limit 8.0h
- Stage71C team totals: **OK** | age 5.31h | limit 8.0h
- Stage71E double chance: **OK** | age 5.31h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.31h | limit 8.0h
- Stage71G DNB: **OK** | age 5.31h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.41h | limit 3.0h
- Stage71I settlement: **OK** | age 1.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.32h | limit 1.0h
- Stage73 internal API: **OK** | age 0.65h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 123.75h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 11.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 107.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 25.80h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 7.09h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.41h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.