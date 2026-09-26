# PBK System Health

Обновлено UTC: 2026-09-26T22:05:56Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 190 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.38h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.21h | limit 1.5h
- Stage57 international: **OK** | age 15.34h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 10.24h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.23h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.68h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.20h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **STALE** | age 38.53h | limit 8.0h
- Stage71C team totals: **OK** | age 3.38h | limit 8.0h
- Stage71E double chance: **OK** | age 3.38h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.38h | limit 8.0h
- Stage71G DNB: **OK** | age 3.38h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.50h | limit 3.0h
- Stage71I settlement: **OK** | age 1.31h | limit 3.0h
- Stage72 data layer: **OK** | age 0.16h | limit 1.0h
- Stage73 internal API: **OK** | age 0.12h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 10.24h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.57h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.68h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.80h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 38.53h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.50h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.