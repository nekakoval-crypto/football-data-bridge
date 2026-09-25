# PBK System Health

Обновлено UTC: 2026-09-25T16:07:05Z
Статус: 🟠 **WARN** | critical 0 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 189 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.18h | limit 1.5h
- Stage57 international: **OK** | age 9.32h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 4.23h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.22h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.61h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.28h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.83h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 8.55h | limit 8.0h
- Stage71C team totals: **OK** | age 3.36h | limit 8.0h
- Stage71E double chance: **OK** | age 3.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.36h | limit 8.0h
- Stage71G DNB: **OK** | age 3.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.46h | limit 3.0h
- Stage71I settlement: **OK** | age 1.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.14h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage59 user execution: age 4.23h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 8.55h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.47h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.