# PBK System Health

Обновлено UTC: 2026-09-29T14:09:10Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 7.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.35h | limit 1.5h
- Stage57 international: **OK** | age 7.33h | limit 30.0h
- Stage58 daily brief: **STALE** | age 11.09h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 16.24h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.56h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.24h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 1.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 14.61h | limit 8.0h
- Stage71C team totals: **OK** | age 1.16h | limit 8.0h
- Stage71E double chance: **OK** | age 1.16h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.16h | limit 8.0h
- Stage71G DNB: **OK** | age 1.16h | limit 8.0h
- Stage71H readiness: **OK** | age 1.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.28h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 11.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.21h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 16.24h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 14.61h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.