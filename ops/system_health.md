# PBK System Health

Обновлено UTC: 2026-09-26T19:05:29Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 190 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 12.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.78h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.11h | limit 1.5h
- Stage57 international: **OK** | age 12.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.23h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.21h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.56h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.67h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **OK** | age 1.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.92h | limit 3.0h
- Stage71 challengers: **STALE** | age 35.52h | limit 8.0h
- Stage71C team totals: **OK** | age 0.38h | limit 8.0h
- Stage71E double chance: **OK** | age 0.38h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.38h | limit 8.0h
- Stage71G DNB: **OK** | age 0.38h | limit 8.0h
- Stage71H readiness: **OK** | age 0.50h | limit 3.0h
- Stage71I settlement: **OK** | age 0.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.04h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 35.52h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.