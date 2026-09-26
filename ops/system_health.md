# PBK System Health

Обновлено UTC: 2026-09-26T00:07:53Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 190 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.56h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.41h | limit 3.0h
- Stage55 context: **OK** | age 0.88h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.19h | limit 1.5h
- Stage57 international: **OK** | age 17.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 12.24h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.26h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.69h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.78h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.87h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.00h | limit 3.0h
- Stage71 challengers: **STALE** | age 16.56h | limit 8.0h
- Stage71C team totals: **OK** | age 5.42h | limit 8.0h
- Stage71E double chance: **OK** | age 5.42h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.42h | limit 8.0h
- Stage71G DNB: **OK** | age 5.42h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.55h | limit 3.0h
- Stage71I settlement: **OK** | age 1.33h | limit 3.0h
- Stage72 data layer: **OK** | age 0.21h | limit 1.0h
- Stage73 internal API: **OK** | age 0.17h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.99h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 12.24h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 16.56h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.55h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.