# PBK System Health

Обновлено UTC: 2026-10-01T13:10:37Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 6.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.27h | limit 3.0h
- Stage55 context: **OK** | age 0.77h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **STALE** | age 30.35h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 44.22h | limit 3.0h
- Stage60 forward performance: **STALE** | age 3.19h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.50h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.62h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.09h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **STALE** | age 13.63h | limit 8.0h
- Stage71C team totals: **OK** | age 0.34h | limit 8.0h
- Stage71E double chance: **OK** | age 0.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.34h | limit 8.0h
- Stage71G DNB: **OK** | age 0.34h | limit 8.0h
- Stage71H readiness: **OK** | age 0.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.15h | limit 1.0h
- Stage73 internal API: **OK** | age 0.05h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 30.35h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 44.21h > 3.00h
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 3.19h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 13.63h > 8.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.