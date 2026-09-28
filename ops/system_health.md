# PBK System Health

Обновлено UTC: 2026-09-28T18:08:18Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.19h | limit 1.5h
- Stage57 international: **OK** | age 11.30h | limit 30.0h
- Stage58 daily brief: **STALE** | age 8.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.16h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.17h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.13h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.76h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.18h | limit 3.0h
- Stage66 attention board: **OK** | age 0.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **STALE** | age 18.61h | limit 8.0h
- Stage71C team totals: **OK** | age 5.33h | limit 8.0h
- Stage71E double chance: **OK** | age 5.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.33h | limit 8.0h
- Stage71G DNB: **OK** | age 5.33h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.43h | limit 3.0h
- Stage71I settlement: **STALE** | age 3.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.20h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 8.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.16h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.13h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.67h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.76h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 18.61h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.43h > 3.00h
- **WARN** `STALE_STAGE` — Stage71I settlement: age 3.23h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.