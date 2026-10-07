# PBK System Health

Обновлено UTC: 2026-10-07T07:10:44Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 0.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.26h | limit 3.0h
- Stage55 context: **OK** | age 0.79h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.27h | limit 1.5h
- Stage57 international: **STALE** | age 64.76h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.08h | limit 3.0h
- Stage59 user execution: **STALE** | age 4.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 48.08h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.61h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.64h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.20h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **OK** | age 7.50h | limit 8.0h
- Stage71C team totals: **OK** | age 0.34h | limit 8.0h
- Stage71E double chance: **OK** | age 0.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.34h | limit 8.0h
- Stage71G DNB: **OK** | age 0.34h | limit 8.0h
- Stage71H readiness: **OK** | age 0.43h | limit 3.0h
- Stage71I settlement: **OK** | age 0.20h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.03h | limit 1.0h
- Stage68 exposure map: **STALE** | age 9.00h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.07h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 64.76h > 30.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 4.21h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 48.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.61h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.70h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.11h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 9.00h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.