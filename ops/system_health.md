# PBK System Health

Обновлено UTC: 2026-10-08T17:09:40Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 10.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.28h | limit 3.0h
- Stage55 context: **OK** | age 0.78h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **STALE** | age 98.75h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 11.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 82.07h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.52h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.62h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.21h | limit 3.0h
- Stage66 attention board: **OK** | age 0.06h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.92h | limit 3.0h
- Stage71 challengers: **STALE** | age 9.41h | limit 8.0h
- Stage71C team totals: **OK** | age 4.28h | limit 8.0h
- Stage71E double chance: **OK** | age 4.28h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.28h | limit 8.0h
- Stage71G DNB: **OK** | age 4.28h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.37h | limit 3.0h
- Stage71I settlement: **OK** | age 0.20h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.00h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 98.75h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 11.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 82.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.92h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 9.41h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.37h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.