# PBK System Health

Обновлено UTC: 2026-09-25T15:06:47Z
Статус: 🟠 **WARN** | critical 0 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 189 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 8.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.12h | limit 1.5h
- Stage57 international: **OK** | age 8.32h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.18h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.16h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.25h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 7.54h | limit 8.0h
- Stage71C team totals: **OK** | age 2.36h | limit 8.0h
- Stage71E double chance: **OK** | age 2.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.36h | limit 8.0h
- Stage71G DNB: **OK** | age 2.36h | limit 8.0h
- Stage71H readiness: **OK** | age 2.46h | limit 3.0h
- Stage71I settlement: **OK** | age 0.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.26h | limit 1.0h
- Stage73 internal API: **OK** | age 0.22h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.22h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.