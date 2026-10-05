# PBK System Health

Обновлено UTC: 2026-10-05T17:08:48Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 10.42h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.29h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.29h | limit 1.5h
- Stage57 international: **OK** | age 26.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 9.96h | limit 3.0h
- Stage59 user execution: **STALE** | age 23.00h | limit 3.0h
- Stage60 forward performance: **STALE** | age 10.05h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.55h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.66h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 10.69h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 2.03h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 5.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 20.34h | limit 8.0h
- Stage71C team totals: **OK** | age 4.28h | limit 8.0h
- Stage71E double chance: **OK** | age 4.28h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.28h | limit 8.0h
- Stage71G DNB: **OK** | age 4.28h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.37h | limit 3.0h
- Stage71I settlement: **OK** | age 0.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.07h | limit 1.0h
- Stage73 internal API: **OK** | age 0.10h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.86h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 9.96h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 23.00h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 10.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.55h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 10.69h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 5.95h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 20.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.37h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.86h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.