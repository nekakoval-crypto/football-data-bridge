# PBK System Health

Обновлено UTC: 2026-09-19T10:06:04Z
Статус: 🟠 **WARN** | critical 0 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 140 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 3.58h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.39h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.22h | limit 1.5h
- Stage57 international: **OK** | age 3.37h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.20h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.23h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.65h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.75h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **OK** | age 2.61h | limit 8.0h
- Stage71C team totals: **OK** | age 3.39h | limit 8.0h
- Stage71E double chance: **OK** | age 3.39h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.39h | limit 8.0h
- Stage71G DNB: **OK** | age 3.39h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.51h | limit 3.0h
- Stage71I settlement: **OK** | age 1.32h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.13h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.20h > 3.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.75h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.78h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.51h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.