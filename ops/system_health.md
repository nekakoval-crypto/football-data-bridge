# PBK System Health

Обновлено UTC: 2026-10-10T21:07:25Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.51h | limit 1.5h
- Stage57 international: **OK** | age 14.26h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 10.19h | limit 3.0h
- Stage60 forward performance: **STALE** | age 134.03h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.25h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.77h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **OK** | age 5.38h | limit 8.0h
- Stage71C team totals: **OK** | age 2.33h | limit 8.0h
- Stage71E double chance: **OK** | age 2.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.33h | limit 8.0h
- Stage71G DNB: **OK** | age 2.33h | limit 8.0h
- Stage71H readiness: **OK** | age 2.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.22h | limit 1.0h
- Stage73 internal API: **OK** | age 0.10h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 10.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 134.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.77h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.