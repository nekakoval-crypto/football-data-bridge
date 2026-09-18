# PBK System Health

Обновлено UTC: 2026-09-18T00:07:25Z
Статус: 🟠 **WARN** | critical 0 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 104 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **STALE** | age 41.56h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.44h | limit 3.0h
- Stage55 context: **OK** | age 0.90h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.25h | limit 1.5h
- Stage57 international: **OK** | age 17.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.07h | limit 3.0h
- Stage59 user execution: **OK** | age 0.27h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.26h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.72h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.80h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.87h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.00h | limit 3.0h
- Stage66 attention board: **OK** | age 0.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.01h | limit 3.0h
- Stage71 challengers: **STALE** | age 8.62h | limit 8.0h
- Stage71C team totals: **OK** | age 5.40h | limit 8.0h
- Stage71E double chance: **OK** | age 5.40h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.40h | limit 8.0h
- Stage71G DNB: **OK** | age 5.40h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.52h | limit 3.0h
- Stage71I settlement: **OK** | age 1.37h | limit 3.0h
- Stage72 data layer: **OK** | age 0.21h | limit 1.0h
- Stage73 internal API: **OK** | age 0.87h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.00h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage53 screener: age 41.56h > 30.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 8.62h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.52h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.