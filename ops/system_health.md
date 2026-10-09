# PBK System Health

Обновлено UTC: 2026-10-09T08:10:18Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 1.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 113.76h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.05h | limit 3.0h
- Stage59 user execution: **OK** | age 1.09h | limit 3.0h
- Stage60 forward performance: **STALE** | age 97.08h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 15.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.16h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.93h | limit 3.0h
- Stage71 challengers: **OK** | age 0.39h | limit 8.0h
- Stage71C team totals: **OK** | age 1.29h | limit 8.0h
- Stage71E double chance: **OK** | age 1.29h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.29h | limit 8.0h
- Stage71G DNB: **OK** | age 1.29h | limit 8.0h
- Stage71H readiness: **OK** | age 1.39h | limit 3.0h
- Stage71I settlement: **OK** | age 1.15h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.24h | limit 1.0h
- Stage68 exposure map: **STALE** | age 15.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 113.76h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 97.08h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.15h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 15.80h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 15.93h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.