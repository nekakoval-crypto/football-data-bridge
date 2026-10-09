# PBK System Health

Обновлено UTC: 2026-10-09T14:11:19Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 7.52h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.34h | limit 1.5h
- Stage57 international: **STALE** | age 119.77h | limit 30.0h
- Stage58 daily brief: **STALE** | age 12.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.11h | limit 3.0h
- Stage60 forward performance: **STALE** | age 103.09h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.55h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.23h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 21.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.16h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **OK** | age 6.41h | limit 8.0h
- Stage71C team totals: **OK** | age 1.33h | limit 8.0h
- Stage71E double chance: **OK** | age 1.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.33h | limit 8.0h
- Stage71G DNB: **OK** | age 1.33h | limit 8.0h
- Stage71H readiness: **OK** | age 1.43h | limit 3.0h
- Stage71I settlement: **OK** | age 1.19h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.29h | limit 1.0h
- Stage68 exposure map: **STALE** | age 21.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 119.77h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 12.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.11h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 103.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 21.82h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.12h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 21.95h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.