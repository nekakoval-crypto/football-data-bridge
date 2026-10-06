# PBK System Health

Обновлено UTC: 2026-10-06T04:09:42Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 21.44h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 37.75h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.09h | limit 3.0h
- Stage59 user execution: **STALE** | age 10.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 21.07h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.60h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.71h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.86h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 1.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.99h | limit 3.0h
- Stage71 challengers: **OK** | age 4.55h | limit 8.0h
- Stage71C team totals: **OK** | age 3.30h | limit 8.0h
- Stage71E double chance: **OK** | age 3.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.30h | limit 8.0h
- Stage71G DNB: **OK** | age 3.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.36h | limit 3.0h
- Stage71I settlement: **OK** | age 1.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.16h | limit 1.0h
- Stage73 internal API: **OK** | age 0.06h | limit 1.0h
- Stage68 exposure map: **STALE** | age 21.88h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 37.75h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 10.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 21.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.36h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 21.88h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.