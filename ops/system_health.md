# PBK System Health

Обновлено UTC: 2026-09-25T09:06:09Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 189 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 2.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.12h | limit 1.5h
- Stage57 international: **OK** | age 2.31h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 10.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.18h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.25h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 1.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 1.53h | limit 8.0h
- Stage71C team totals: **OK** | age 2.33h | limit 8.0h
- Stage71E double chance: **OK** | age 2.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.33h | limit 8.0h
- Stage71G DNB: **OK** | age 2.33h | limit 8.0h
- Stage71H readiness: **OK** | age 2.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.06h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 10.22h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.