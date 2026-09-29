# PBK System Health

Обновлено UTC: 2026-09-29T00:09:11Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.52h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.40h | limit 3.0h
- Stage55 context: **OK** | age 0.89h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 17.31h | limit 30.0h
- Stage58 daily brief: **STALE** | age 14.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.18h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.24h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 9.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 8.68h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 11.77h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.23h | limit 3.0h
- Stage66 attention board: **OK** | age 0.14h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.01h | limit 3.0h
- Stage71 challengers: **OK** | age 0.61h | limit 8.0h
- Stage71C team totals: **STALE** | age 11.34h | limit 8.0h
- Stage71E double chance: **STALE** | age 11.34h | limit 8.0h
- Stage71F European handicap: **STALE** | age 11.34h | limit 8.0h
- Stage71G DNB: **STALE** | age 11.34h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.50h | limit 3.0h
- Stage71I settlement: **OK** | age 1.35h | limit 3.0h
- Stage72 data layer: **OK** | age 0.16h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.00h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 14.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 9.15h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 8.68h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 11.77h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 11.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 11.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 11.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 11.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.50h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.