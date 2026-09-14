# PBK System Health

Обновлено UTC: 2026-09-14T18:06:25Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 91 | schema v14
- Stage73 Internal API: tests **16/16** | API v1
- Optional stable sources pending: standings_snapshots.csv

## Свежесть этапов
- Stage53 screener: **OK** | age 11.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.15h | limit 1.5h
- Stage57 international: **OK** | age 11.31h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **OK** | age 0.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 4.19h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.64h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.27h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.83h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.18h | limit 3.0h
- Stage66 attention board: **OK** | age 0.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.99h | limit 3.0h
- Stage71 challengers: **OK** | age 2.55h | limit 8.0h
- Stage71C team totals: **OK** | age 5.33h | limit 8.0h
- Stage71E double chance: **OK** | age 5.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.33h | limit 8.0h
- Stage71G DNB: **OK** | age 5.33h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.13h | limit 1.0h
- Stage73 internal API: **OK** | age 0.83h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 4.19h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.44h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.