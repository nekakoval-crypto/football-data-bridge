# PBK System Health

Обновлено UTC: 2026-10-08T21:09:39Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **STALE** | age 102.75h | limit 30.0h
- Stage58 daily brief: **STALE** | age 10.05h | limit 3.0h
- Stage59 user execution: **OK** | age 0.16h | limit 3.0h
- Stage60 forward performance: **STALE** | age 86.06h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.54h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.65h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.25h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 13.41h | limit 8.0h
- Stage71C team totals: **OK** | age 2.34h | limit 8.0h
- Stage71E double chance: **OK** | age 2.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.34h | limit 8.0h
- Stage71G DNB: **OK** | age 2.34h | limit 8.0h
- Stage71H readiness: **OK** | age 2.42h | limit 3.0h
- Stage71I settlement: **OK** | age 0.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.06h | limit 1.0h
- Stage73 internal API: **OK** | age 0.26h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 102.75h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 10.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 86.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.79h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 13.41h > 8.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.92h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.