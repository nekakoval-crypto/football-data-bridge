# PBK System Health

Обновлено UTC: 2026-09-24T21:06:04Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 189 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.78h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **OK** | age 14.32h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 12.19h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.17h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.59h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.68h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.81h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 1.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **OK** | age 5.52h | limit 8.0h
- Stage71C team totals: **OK** | age 2.38h | limit 8.0h
- Stage71E double chance: **OK** | age 2.38h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.38h | limit 8.0h
- Stage71G DNB: **OK** | age 2.38h | limit 8.0h
- Stage71H readiness: **OK** | age 2.49h | limit 3.0h
- Stage71I settlement: **OK** | age 0.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.11h | limit 1.0h
- Stage73 internal API: **OK** | age 0.05h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 12.19h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.