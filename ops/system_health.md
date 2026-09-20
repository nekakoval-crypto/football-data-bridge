# PBK System Health

Обновлено UTC: 2026-09-20T10:05:57Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 162 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 3.57h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.39h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.16h | limit 1.5h
- Stage57 international: **OK** | age 3.36h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **OK** | age 0.24h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.23h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.74h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.83h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **OK** | age 2.59h | limit 8.0h
- Stage71C team totals: **OK** | age 3.37h | limit 8.0h
- Stage71E double chance: **OK** | age 3.37h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.37h | limit 8.0h
- Stage71G DNB: **OK** | age 3.37h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.49h | limit 3.0h
- Stage71I settlement: **OK** | age 1.32h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.16h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.17h > 2.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.49h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.