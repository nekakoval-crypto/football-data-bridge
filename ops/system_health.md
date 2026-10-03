# PBK System Health

Обновлено UTC: 2026-10-03T01:07:46Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 18.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.26h | limit 3.0h
- Stage55 context: **OK** | age 0.73h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.28h | limit 1.5h
- Stage57 international: **OK** | age 18.28h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 29.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 39.15h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 8.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 7.25h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **OK** | age 1.10h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.96h | limit 3.0h
- Stage71 challengers: **OK** | age 1.56h | limit 8.0h
- Stage71C team totals: **OK** | age 0.34h | limit 8.0h
- Stage71E double chance: **OK** | age 0.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.34h | limit 8.0h
- Stage71G DNB: **OK** | age 0.34h | limit 8.0h
- Stage71H readiness: **OK** | age 0.42h | limit 3.0h
- Stage71I settlement: **OK** | age 0.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.16h | limit 1.0h
- Stage73 internal API: **OK** | age 0.07h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.90h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.02h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 29.21h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 39.15h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 8.14h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 7.25h > 2.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.96h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.