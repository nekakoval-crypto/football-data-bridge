# PBK System Health

Обновлено UTC: 2026-10-06T10:09:24Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 3.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 43.74h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 16.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 27.06h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.60h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.23h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 7.85h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.23h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **OK** | age 2.44h | limit 8.0h
- Stage71C team totals: **OK** | age 3.32h | limit 8.0h
- Stage71E double chance: **OK** | age 3.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.32h | limit 8.0h
- Stage71G DNB: **OK** | age 3.32h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.40h | limit 3.0h
- Stage71I settlement: **OK** | age 1.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.16h | limit 1.0h
- Stage73 internal API: **OK** | age 0.06h | limit 1.0h
- Stage68 exposure map: **STALE** | age 27.87h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 43.74h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 16.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 27.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.60h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 7.85h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.40h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 27.87h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.