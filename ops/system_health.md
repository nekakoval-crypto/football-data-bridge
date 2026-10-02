# PBK System Health

Обновлено UTC: 2026-10-02T09:08:43Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 2.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.10h | limit 1.5h
- Stage57 international: **OK** | age 2.29h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 13.22h | limit 3.0h
- Stage60 forward performance: **STALE** | age 23.16h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.16h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.73h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 1.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 1.49h | limit 8.0h
- Stage71C team totals: **OK** | age 2.33h | limit 8.0h
- Stage71E double chance: **OK** | age 2.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.33h | limit 8.0h
- Stage71G DNB: **OK** | age 2.33h | limit 8.0h
- Stage71H readiness: **OK** | age 2.43h | limit 3.0h
- Stage71I settlement: **OK** | age 0.29h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.06h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 13.22h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 23.16h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.73h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.